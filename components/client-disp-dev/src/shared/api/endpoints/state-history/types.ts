import type { Pagination } from '@/shared/api/types';

/** Типы записи истории статусов. */
const StateHistoryTypeName = {
  CYCLE_STATE_HISTORY: 'cycle_state_history',
  FULL_SHIFT_STATE_HISTORY: 'full_shift_state_history',
} as const;

/** Представляет базовую модель записи в истории статусов. */
interface StateHistoryBase {
  /** Возвращает тип записи. */
  readonly type_name: (typeof StateHistoryTypeName)[keyof typeof StateHistoryTypeName];
  /** Возвращает идентификатор. */
  readonly id: string;
  /** Возвращает время начала статуса. */
  readonly timestamp: string;
  /** Возвращает идентификатор машины. */
  readonly vehicle_id: number;
  /** Возвращает источник изменения статуса. */
  readonly source: string;
  /** Возвращает статус. */
  readonly state: string;
}

/** Представляет модель записи в истории статусов. */
export interface CycleStateHistory extends StateHistoryBase {
  /** Возвращает тип записи. */
  readonly type_name: typeof StateHistoryTypeName.CYCLE_STATE_HISTORY;
  /** Возвращает идентификатор цикла. */
  readonly cycle_id: string | null;
  /** Возвращает идентификатор места. */
  readonly place_id: number | null;
  /** Возвращает идентификатор задачи. */
  readonly task_id: string | null;
}

/** Представляет модель записи в истории статусов. */
export interface FullShiftStateHistory extends StateHistoryBase {
  /** Возвращает тип записи. */
  readonly type_name: typeof StateHistoryTypeName.FULL_SHIFT_STATE_HISTORY;
  /** Возвращает номер смены. */
  readonly shift_num: number;
  /** Возвращает дату смены. */
  readonly shift_date: string;
  /** Возвращает длительность простоя в секундах (null если нет данных). */
  readonly idle_duration: number | null;
  /** Возвращает длительность работы в секундах (null если нет данных). */
  readonly work_duration: number | null;
}

/** Представляет модель записи в истории статусов. */
export type StateHistory = CycleStateHistory | FullShiftStateHistory;

/** Представляет параметры запроса для получения истории статусов. */
export interface StateHistoryQueryArg {
  /** Возвращает дату начала периода. */
  readonly fromDate: string;
  /** Возвращает дату окончания периода. */
  readonly toDate: string;
  /** Возвращает номер смены начала периода. */
  readonly fromShiftNum: number;
  /** Возвращает номер смены окончания периода. */
  readonly toShiftNum: number;
  /** Возвращает список идентификаторов транспортных средств. */
  readonly vehicleIds?: readonly number[];
  /** Возвращает признак запроса полносменных статусов. */
  readonly isFullShift?: boolean;
}

/** Представляет модель данных, получаемую по запросу истории статусов. */
export interface StateHistoryResponse extends Pagination {
  /** Возвращает список записей в истории статусов. */
  readonly items: readonly StateHistory[];
}

/** Представляет параметры запроса для получения данных о состоянии оборудования на момент времени. */
export interface StateHistoryLastStateQueryArgs {
  /** Возвращает идентификатор оборудования. */
  readonly vehicle_id: number;
  /** Возвращает момент времени. */
  readonly timestamp: string;
}

/** Представляет модель данных получаемую по запросу состояния оборудования на момент времени. */
export interface StateHistoryLastStateResponse {
  /** Возвращает статус. */
  readonly state: string;
  /** Возвращает идентификатор места. */
  readonly place_id: number | null;
}

/** Представляет модель данных для создания/редактирования элемента истории статусов. */
export interface CreateUpdateStateHistoryRequestItem {
  /** Возвращает идентификатор. */
  readonly id: string | null;
  /** Возвращает время начала статуса. */
  readonly timestamp: string | null;
  /** Возвращает системное имя статуса. */
  readonly system_name: string;
  /** Возвращает признак того, что статус является системным. */
  readonly system_status: boolean;
  /** Возвращает признак того, что статус является окончанием предыдущего цикла. */
  readonly is_end_of_cycle?: boolean;
  /** Возвращает идентификатор цикла. */
  readonly cycle_id?: string | null;
}

/** Представляет модель данных для создания/редактирования элемента истории статусов для выбранного транспортного средства. */
export interface CreateUpdateStateHistoryRequest {
  /** Возвращает идентификатор транспортного средства. */
  readonly vehicle_id: number;
  /** Возвращает список статусов. */
  readonly items: readonly CreateUpdateStateHistoryRequestItem[];
}

/** Представляет модель данных, получаемую при создании/редактировании элементов истории статусов для выбранного транспортного средства. */
export interface CreateUpdateStateHistoryResponse {
  /** Возвращает признак успешности операции. */
  readonly success: boolean;
  /** Возвращает сообщение. */
  readonly message: string;
  /** Возвращает список результатов. */
  readonly results: readonly {
    /** Возвращает идентификатор. */
    readonly id: string;
    /** Возвращает тип операции. */
    readonly operation: 'created' | 'updated';
    /** Возвращает статус. */
    readonly state: string;
    /** Возвращает время начала статуса. */
    readonly timestamp: string;
    /** Возвращает идентификатор цикла. */
    readonly cycle_id: string | null;
    /** Возвращает действие над циклом. */
    readonly cycle_action: 'created' | 'completed' | null;
  }[];
  /** Возвращает количество созданных циклов. */
  readonly cycles_created: number;
  /** Возвращает количество завершенных циклов. */
  readonly cycles_completed: number;
}

/** Представляет модель данных для удаления статуса из истории. */
export interface DeleteStateHistoryRequest {
  /** Возвращает идентификатор. */
  readonly id: string;
  /** Возвращает признак подтверждения удаления. */
  readonly confirm: boolean;
}

/** Представляет модель данных, получаемую при запросе на удаление статуса из истории. */
export interface DeleteStateHistoryResponse {
  /** Возвращает признак успешности операции. */
  readonly success: boolean;
  /** Возвращает сообщение для подтверждения удаления. */
  readonly message: string;
  /** Возвращает идентификатор цикла, который будет удален. */
  readonly cycle_id: string | null;
  /** Возвращает идентификатор удаленной записи. */
  readonly deleted_record_id: string | null;
  /** Возвращает признак, был ли удален цикл. */
  readonly cycle_deleted: boolean;
  /** Возвращает признак, был ли удален рейс. */
  readonly trip_deleted: boolean;
  /** Возвращает список очищенных полей в цикле/рейсе. */
  readonly fields_cleared: readonly string[];
}

/**
 * Сужает тип статуса до статуса цикла.
 *
 * @param state статус.
 */
export function isCycleStateHistory(state: StateHistory): state is CycleStateHistory {
  return state.type_name === StateHistoryTypeName.CYCLE_STATE_HISTORY;
}

/**
 * Сужает тип статуса до статуса, который является полносменным.
 *
 * @param state статус.
 */
export function isFullShiftStateHistory(state: StateHistory): state is FullShiftStateHistory {
  return state.type_name === StateHistoryTypeName.FULL_SHIFT_STATE_HISTORY;
}
