import { rtkApi } from '@/shared/api/rtk-api';
import type { VehicleState } from '@/shared/api/types/vehicle-events';
import type {
  AvailableStateItem,
  VehicleStateResponse,
  VehicleStateTransitionBody,
} from '@/shared/api/types/vehicle-state';
import { stateEventReceived } from '@/shared/lib/vehicle-events';

/** Ответ trip service: массив или объект с полем states/items — приводим к AvailableStateItem[]. */
function normalizeAvailableStatesPayload(raw: unknown): AvailableStateItem[] {
  const asArray = () => {
    if (Array.isArray(raw)) {
      return raw as unknown[];
    }
    if (raw && typeof raw === 'object') {
      const o = raw as Record<string, unknown>;
      const nested = o.states ?? o.items ?? o.available_states ?? o.data;
      if (Array.isArray(nested)) {
        return nested as unknown[];
      }
    }
    return [] as unknown[];
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
        dispatch(
          stateEventReceived({
            event_type: 'state_event',
            status: arg.new_state as VehicleState,
            timestamp: new Date().toISOString(),
          }),
        );
      },
    }),
  }),
});

export const { useGetVehicleStateQuery, useGetAvailableStatesQuery, useSetVehicleStateTransitionMutation } =
  vehicleStateApi;
