/** Базовые коды state machine trip-service (известные литералы). */
export const VEHICLE_STATE_MACHINE_CODES = [
  'idle',
  'moving_empty',
  'stopped_empty',
  'loading',
  'moving_loaded',
  'stopped_loaded',
  'unloading',
] as const;

export type VehicleStateMachineCode = (typeof VEHICLE_STATE_MACHINE_CODES)[number];

/**
 * Состояния State Machine борта: стандартные коды + произвольный `system_name` из enterprise `/api/statuses`.
 */
export type VehicleState = VehicleStateMachineCode | (string & {});

/** Событие изменения состояния борта. */
export interface StateEvent {
  /** Тип события: всегда `state_event`. */
  readonly event_type: 'state_event';
  /** Новое состояние бортовой state machine. */
  readonly status: VehicleState;
  /** Метка времени события (строка, в формате как возвращает бэкенд). */
  readonly timestamp: string;
}

/** Событие смены метки/места борта. */
export interface LocationEvent {
  /** Тип события: всегда `location_event`. */
  readonly event_type: 'location_event';
  /** ID тега (если борт находится на теге), иначе `null`. */
  readonly tag_id: string | null;
  /** Имя тега (если борт находится на теге), иначе `null`. */
  readonly tag_name: string | null;
  /** ID места (если борт находится на месте), иначе `null`. */
  readonly place_id: string | null;
  /** Имя места (если борт находится на месте), иначе `null`. */
  readonly place_name: string | null;
  /** Тип места (если борт находится на месте), иначе `null`. */
  readonly place_type: string | null;
}

/** Событие получения данных весового датчика. */
export interface WeightEvent {
  /** Тип события: всегда `weight_event`. */
  readonly event_type: 'weight_event';
  /** Статус датчика/события (как возвращает бэкенд). */
  readonly status: string;
  /** Числовое значение веса. */
  readonly value: number;
}

/** Событие Wi-Fi коннекта борта с сервером. */
export interface WifiEvent {
  readonly event_type: 'wifi_event';
  readonly status: 'on' | 'off';
}

/** Необрабатываемое событие (ошибки бэкенда). */
export interface UnknownEvent {
  /** Тип события: всегда `unknown_event`. */
  readonly event_type: 'unknown_event';
  /** Любые дополнительные поля, возвращенные бэкендом. */
  readonly [key: string]: unknown;
}

/**
 * Алерт об изменении назначений для борта (из dispatcher/назначений).
 * Используется для повторной загрузки актуальных `shift_tasks` на борте.
 */
export interface AssignmentsAlertEvent {
  /** Тип события: всегда `assignments_alert`. */
  readonly event_type: 'assignments_alert';
  /** Содержимое события об изменении назначений. */
  readonly payload: {
    /** Идентификатор события/записи. */
    readonly id: number;
    /** Статус в контексте назначений/смены (как возвращает бэкенд). */
    readonly status: string;
    /** Номер смены. */
    readonly shift_num: number;
    /** Время создания записи. */
    readonly created_at: string;
    /** Дата смены. */
    readonly shift_date: string;
    /** Время последнего обновления записи. */
    readonly updated_at: string;
    /** ID борта. */
    readonly vehicle_id: number;
    /** Тип источника (откуда пришло изменение). */
    readonly source_kind: string | null;
    /** Тип назначения (куда применилось изменение). */
    readonly target_kind: string;
    /** ID гаражной точки источника или `null`. */
    readonly source_garage_place_id: number | null;
    /** ID гаражной точки назначения или `null`. */
    readonly target_garage_place_id: number | null;
    /** ID точки маршрута A источника или `null`. */
    readonly source_route_place_a_id: number | null;
    /** ID точки маршрута B источника или `null`. */
    readonly source_route_place_b_id: number | null;
    /** ID точки маршрута A назначения или `null`. */
    readonly target_route_place_a_id: number | null;
    /** ID точки маршрута B назначения или `null`. */
    readonly target_route_place_b_id: number | null;
    /** Дополнительные поля из контракта бэкенда. */
    readonly [key: string]: unknown;
  };
  /** Набор полей, связанных с сообщением (если бэкенд их передает). */
  readonly message_data?: {
    /** Идентификатор сообщения. */
    readonly message_id?: string;
    /** Тип/категория сообщения. */
    readonly message_type?: string;
    /** Код/тип события внутри сообщения. */
    readonly message_event?: string;
    /** Метка времени сообщения. */
    readonly message_timestamp?: string;
    /** Дополнительные поля сообщения. */
    readonly [key: string]: unknown;
  };
  /** Любые дополнительные корневые поля события. */
  readonly [key: string]: unknown;
}

/** Дискриминированное объединение всех событий стрима борта. */
export type VehicleStreamEvent =
  | StateEvent
  | LocationEvent
  | WeightEvent
  | WifiEvent
  | AssignmentsAlertEvent
  | UnknownEvent;
