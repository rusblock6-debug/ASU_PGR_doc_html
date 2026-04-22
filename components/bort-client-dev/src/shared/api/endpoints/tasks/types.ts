/**
 * DTO маршрутных заданий (Trip Service).
 */

/**
 * Статусы маршрутного задания в Trip Service (строковые значения API).
 */
export type TripStatusRouteEnum =
  | 'ACTIVE'
  | 'REJECTED'
  | 'SENT'
  | 'DELIVERED'
  | 'COMPLETED'
  | 'EMPTY'
  | 'PAUSED'
  | 'IN_PROGRESS';

/**
 * Стандартный пагинированный ответ API.
 */
export interface PaginatedResponse<T> {
  /** Элементы текущей страницы. */
  readonly items: T[];
  /** Общее количество элементов во всей выборке. */
  readonly total: number;
  /** Текущая страница. */
  readonly page: number;
  /** Размер страницы. */
  readonly size: number;
  /** Общее количество страниц. */
  readonly pages: number;
}

/**
 * Маршрутное задание смены.
 */
export interface RouteTaskResponse {
  /** Время создания маршрутного задания. */
  readonly created_at: string;
  /** Время последнего обновления маршрутного задания. */
  readonly updated_at: string;
  /** ID сменного задания, к которому относится маршрутное задание. */
  readonly shift_task_id: string | null;
  /** Порядок выполнения внутри смены/маршрута. */
  readonly route_order: number;
  /** ID точки A маршрута. */
  readonly place_a_id: number;
  /** ID точки B маршрута. */
  readonly place_b_id: number;
  /** Тип маршрутного задания (как указывает бэкенд). */
  readonly type_task: string;
  /** Плановое количество рейсов. */
  readonly planned_trips_count: number;
  /** Фактическое количество рейсов. */
  readonly actual_trips_count: number;
  /** Статус маршрутного задания. */
  readonly status: string;
  /** Произвольные данные маршрута. */
  readonly route_data: Record<string, unknown> | null;
  /** Плановый объем (если применимо). */
  readonly volume: number | null;
  /** Вес (если применимо). */
  readonly weight: number | null;
  /** Сообщение/заметка по заданию (если применимо). */
  readonly message: string | null;
  /** Идентификатор маршрутного задания. */
  readonly id: string;
}

/**
 * Частичное обновление маршрутного задания.
 */
export interface RouteTaskUpdateBody {
  /** Обновление статуса маршрутного задания. */
  readonly status?: TripStatusRouteEnum;
  /** Перевязка на другое сменное задание. */
  readonly shift_task_id?: string | null;
  /** Изменение порядка маршрута. */
  readonly route_order?: number | null;
  /** Обновление точки A. */
  readonly place_a_id?: number | null;
  /** Обновление точки B. */
  readonly place_b_id?: number | null;
  /** Изменение типа задания. */
  readonly type_task?: string | null;
  /** Изменение планового количества рейсов. */
  readonly planned_trips_count?: number | null;
  /** Изменение фактического количества рейсов. */
  readonly actual_trips_count?: number | null;
  /** Изменение route_data. */
  readonly route_data?: Record<string, unknown> | null;
  /** Изменение объема. */
  readonly volume?: number | null;
  /** Изменение веса. */
  readonly weight?: number | null;
  /** Изменение сообщения. */
  readonly message?: string | null;
}

export type ActiveTaskResponse = Record<string, unknown>;

/**
 * Параметры запроса списка маршрутных заданий.
 */
export interface GetRouteTasksArgs {
  readonly page?: number;
  readonly size?: number;
  readonly shift_task_id?: string | null;
  readonly task_status?: TripStatusRouteEnum | null;
}
