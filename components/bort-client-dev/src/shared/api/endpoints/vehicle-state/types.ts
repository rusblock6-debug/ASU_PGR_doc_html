/**
 * Элемент GET /api/state/available-states (trip service).
 */
export interface AvailableStateItem {
  /** Идентификатор доступного state item. */
  readonly id: string;
  /** Код из state machine (например idle, loading), если бэкенд отдаёт. */
  readonly code?: string;
  /** Человекочитаемое имя, если отличается от кода. */
  readonly name?: string;
}

/**
 * Ответ GET /api/state (trip service).
 */
export interface VehicleStateResponse {
  /** Текущее состояние (как возвращает trip service). */
  readonly state?: string | null;
  /** Последний известный ID тега. */
  readonly last_tag_id?: string | null;
  /** Последний известный ID места. */
  readonly last_place_id?: number | string | null;
  /** Время последнего перехода (как возвращает бэкенд). */
  readonly last_transition?: string | number | null;
  /** Дополнительные поля из ответа бэкенда. */
  readonly [key: string]: unknown;
}

/** Тело POST /api/state/transition (trip service). */
export interface VehicleStateTransitionBody {
  /** Новое состояние (из state machine). */
  readonly new_state: string;
  /** Причина перехода (как требуется бэкендом). */
  readonly reason: string;
  /** Комментарий к переходу. */
  readonly comment: string;
}
