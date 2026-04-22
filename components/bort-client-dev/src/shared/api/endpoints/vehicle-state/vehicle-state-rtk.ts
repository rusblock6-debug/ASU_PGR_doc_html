import { rtkApi } from '@/shared/api/rtk-api';
import type { VehicleState, VehicleStreamEvent } from '@/shared/api/types/vehicle-events';
import { VEHICLE_ID_STR } from '@/shared/config/env';

import type { AvailableStateItem, VehicleStateResponse, VehicleStateTransitionBody } from './types';

const INITIAL_RETRY_MS = 2_000;
const MAX_RETRY_MS = 30_000;

/** Снимок последних событий борта, хранимый в кеше RTK Query SSE-подписки. */
interface VehicleEventsSnapshot {
  stateStatus: VehicleState | null;
  stateChangedAt: string | null;
  locationPlaceName: string | null;
  locationTagName: string | null;
  weightValue: number | null;
  wifiConnected: boolean | null;
}

/** Начальный снимок (все поля null) для queryFn. */
const createInitialVehicleEventsSnapshot = (): VehicleEventsSnapshot => ({
  stateStatus: null,
  stateChangedAt: null,
  locationPlaceName: null,
  locationTagName: null,
  weightValue: null,
  wifiConnected: null,
});

/** Применяет state_event к снимку (статус + timestamp). */
const applyStateEvent = (draft: VehicleEventsSnapshot, payload: { status: VehicleState; timestamp: string }) => {
  draft.stateStatus = payload.status;
  draft.stateChangedAt = payload.timestamp;
};

/** Обработчик SSE-сообщений — обновляет кеш подписки и инвалидирует задачи при assignments_alert. */
function handleVehicleStreamMessage(
  data: VehicleStreamEvent,
  updateCachedData: (recipe: (draft: VehicleEventsSnapshot) => void) => void,
  dispatch: (action: unknown) => void,
) {
  switch (data.event_type) {
    case 'state_event':
      updateCachedData((draft) => {
        applyStateEvent(draft, data);
      });
      break;
    case 'location_event':
      updateCachedData((draft) => {
        draft.locationPlaceName = data.place_name;
        draft.locationTagName = data.tag_name;
      });
      break;
    case 'weight_event':
      updateCachedData((draft) => {
        draft.weightValue = data.value;
      });
      break;
    case 'wifi_event':
      updateCachedData((draft) => {
        draft.wifiConnected = data.status === 'on';
      });
      break;
    case 'assignments_alert':
      if (data.message_data?.message_event === 'create') {
        dispatch(rtkApi.util.invalidateTags(['ShiftTask', 'RouteTask']));
      }
      break;
    default:
      break;
  }
}

/** Ответ trip service: массив или объект с полем states/items — приводим к AvailableStateItem[]. */
function normalizeAvailableStatesPayload(raw: unknown): AvailableStateItem[] {
  const asArray = (): unknown[] => {
    if (Array.isArray(raw)) {
      return raw;
    }
    if (raw && typeof raw === 'object') {
      const o = raw as Record<string, unknown>;
      const nested = o.states ?? o.items ?? o.available_states ?? o.data;
      if (Array.isArray(nested)) {
        return nested;
      }
    }
    return [];
  };

  return asArray().map((item, i) => {
    if (typeof item === 'string') {
      return { id: `state-${i}`, code: item, name: item };
    }
    if (item && typeof item === 'object') {
      const o = item as Record<string, unknown>;
      const pickId = () => {
        if (typeof o.id === 'string' || typeof o.id === 'number') {
          return String(o.id);
        }
        if (typeof o.code === 'string') {
          return o.code;
        }
        if (typeof o.state_id === 'string' || typeof o.state_id === 'number') {
          return String(o.state_id);
        }
        return `state-${i}`;
      };
      const id = pickId();
      const code = o.code ?? o.state ?? o.status;
      const name = o.name ?? o.label ?? o.title ?? o.description;
      return {
        id,
        code: typeof code === 'string' ? code : undefined,
        name: typeof name === 'string' ? name : undefined,
      };
    }
    return { id: `state-${i}` };
  });
}

const vehicleStateApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getVehicleState: build.query<VehicleStateResponse, void>({
      query: () => '/state',
      providesTags: ['VehicleState'],
    }),
    getAvailableStates: build.query<AvailableStateItem[], void>({
      query: () => '/state/available-states',
      transformResponse: (raw: unknown) => normalizeAvailableStatesPayload(raw),
    }),
    setVehicleStateTransition: build.mutation<unknown, VehicleStateTransitionBody>({
      query: (body) => ({ url: '/state/transition', method: 'POST', body }),
      invalidatesTags: ['VehicleState'],
      async onQueryStarted(arg, { dispatch, queryFulfilled }) {
        await queryFulfilled;
        dispatch(patchVehicleStateSnapshot(arg.new_state as VehicleState, new Date().toISOString()));
      },
    }),

    /**
     * SSE-подписка на события борта `/api/events/stream/{vehicleId}`.
     * Обрабатывает state/location/weight/assignments_alert; при обрыве — exponential backoff.
     */
    subscribeVehicleEventsStream: build.query<VehicleEventsSnapshot, string>({
      queryFn: () => ({ data: createInitialVehicleEventsSnapshot() }),
      keepUnusedDataFor: 0,

      async onCacheEntryAdded(vehicleId, { cacheDataLoaded, cacheEntryRemoved, dispatch, updateCachedData }) {
        await cacheDataLoaded;

        const base = import.meta.env.VITE_API_URL || '';
        const url = `${base}/api/events/stream/${encodeURIComponent(vehicleId)}`;

        let source = null as EventSource | null;
        let retryMs = INITIAL_RETRY_MS;
        let retryTimer = null as ReturnType<typeof setTimeout> | null;
        let disposed = false;

        const scheduleRetry = () => {
          retryTimer = setTimeout(connect, retryMs);
          retryMs = Math.min(retryMs * 2, MAX_RETRY_MS);
        };

        const connect = () => {
          if (disposed) return;

          source = new EventSource(url);

          source.addEventListener('open', () => {
            retryMs = INITIAL_RETRY_MS;
          });

          source.addEventListener('message', (event: MessageEvent<string>) => {
            try {
              const data = JSON.parse(event.data) as VehicleStreamEvent;
              handleVehicleStreamMessage(data, updateCachedData, dispatch);
            } catch {
              // malformed JSON — пропускаем
            }
          });

          source.addEventListener('error', () => {
            source?.close();
            source = null;
            if (disposed) return;
            scheduleRetry();
          });
        };

        connect();

        await cacheEntryRemoved;
        disposed = true;
        if (retryTimer != null) clearTimeout(retryTimer);
        if (source) source.close();
      },
    }),
  }),
});

export const {
  useGetVehicleStateQuery,
  useGetAvailableStatesQuery,
  useSetVehicleStateTransitionMutation,
  useSubscribeVehicleEventsStreamQuery,
} = vehicleStateApi;

/** Обновляет кеш SSE-подписки вручную (для сидинга из REST). */
export const patchVehicleEventsSnapshot = (recipe: (draft: VehicleEventsSnapshot) => void) =>
  vehicleStateApi.util.updateQueryData('subscribeVehicleEventsStream', VEHICLE_ID_STR, recipe);

/** Патчит статус и timestamp в кеше SSE-подписки (после transition / сидинга). */
export const patchVehicleStateSnapshot = (status: VehicleState, timestamp: string) =>
  patchVehicleEventsSnapshot((draft) => {
    applyStateEvent(draft, { status, timestamp });
  });

const selectVehicleEventsResult = vehicleStateApi.endpoints.subscribeVehicleEventsStream.select(VEHICLE_ID_STR);

const selectVehicleEventsSnapshot = (state: RootState) => selectVehicleEventsResult(state)?.data;

export const selectVehicleState = (state: RootState) => selectVehicleEventsSnapshot(state)?.stateStatus ?? null;
export const selectStateChangedAt = (state: RootState) => selectVehicleEventsSnapshot(state)?.stateChangedAt ?? null;
export const selectLocationPlaceName = (state: RootState) =>
  selectVehicleEventsSnapshot(state)?.locationPlaceName ?? null;
export const selectLocationTagName = (state: RootState) => selectVehicleEventsSnapshot(state)?.locationTagName ?? null;
export const selectWeightValue = (state: RootState) => selectVehicleEventsSnapshot(state)?.weightValue ?? null;
export const selectWifiConnected = (state: RootState) => selectVehicleEventsSnapshot(state)?.wifiConnected ?? null;
