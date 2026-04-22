import { hasValue } from '@/shared/lib/has-value';

/** Максимальное число попыток переподключения WS. */
const MAX_WS_RECONNECT_ATTEMPTS = 5;

/** Формат сообщения vehicle_location_update из WebSocket /ws/vehicle-tracking. */
interface WsLocationMessage {
  /** Тип события. */
  readonly type?: string;
  /** Данные события с координатами машины. */
  readonly data?: {
    /** Идентификатор транспортного средства. */
    readonly vehicle_id: string;
    /** Широта. */
    readonly lat?: number;
    /** Долгота. */
    readonly lon?: number;
  };
}

/**
 * Создает подключение к WebSocket /ws/vehicle-tracking.
 * Вызов `start()` открывает соединение, `onUpdate` срабатывает при каждом обновлении координат.
 * Автоматически переподключается (максимум {@link MAX_WS_RECONNECT_ATTEMPTS} попыток).
 */
export function createVehicleTrackingWS(onUpdate: (vehicleId: number, lat: number, lon: number) => void) {
  let ws: WebSocket | null = null;
  let reconnectAttempts = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;
  let started = false;

  /** Создает WS-соединение и добавляет обработчики. */
  const connect = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const instance = new WebSocket(`${protocol}//${window.location.host}/ws/vehicle-tracking`);

    instance.onopen = () => {
      reconnectAttempts = 0;
    };

    instance.onmessage = (event: MessageEvent<string>) => {
      let message: WsLocationMessage;
      try {
        message = JSON.parse(event.data) as WsLocationMessage;
      } catch {
        return;
      }

      if (message.type !== 'vehicle_location_update' || !message.data) return;

      const { vehicle_id: vehicleId, lat, lon } = message.data;
      if (!hasValue(lat) || !hasValue(lon)) return;

      onUpdate(Number(vehicleId), lat, lon);
    };

    instance.onclose = () => {
      if (disposed) return;
      if (reconnectAttempts < MAX_WS_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        reconnectTimer = setTimeout(connect, 1_000 * reconnectAttempts);
      }
    };

    ws = instance;
  };

  return {
    /** Открывает WS-соединение. Повторные вызовы игнорируются. */
    start() {
      if (started || disposed) return;
      started = true;
      connect();
    },

    /** Закрывает соединение и отменяет переподключение. */
    dispose() {
      disposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    },
  };
}
