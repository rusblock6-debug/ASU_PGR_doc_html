import type { VehicleType } from '@/shared/api/endpoints/vehicles';

export type AssignPlaceType = 'ROUTE' | 'NO_TASK' | 'GARAGE';

/** Представляет модель техники в контексте управления техникой. */
export interface VehicleFleetControl {
  /** Возвращает тип оборудования. */
  readonly vehicle_type: VehicleType;
  /** Возвращает идентификатор. */
  readonly id: number;
  /** Возвращает наименование. */
  readonly name: string;
  /** Возвращает статус. */
  readonly state: string;
  /** Возвращает признак active/pending в рамках текущего контекста. */
  readonly is_assigned: boolean;
}

/** Представляет модель гаража в контексте управления техникой. */
interface GarageFleetControl {
  /** Возвращает идентификатор. */
  readonly id: number;
  /** Возвращает наименование. */
  readonly name: string;
  /** Возвращает список техники "В простое". */
  readonly vehicles?: readonly VehicleFleetControl[];
}

/** Представляет модель техники в контексте управления техникой. */
export interface RouteFleetControl {
  /** Возвращает идентификатор места погрузки. */
  readonly place_a_id: number;
  /** Возвращает идентификатор места разгрузки. */
  readonly place_b_id: number;
  /** Возвращает идентификатор маршрута. */
  readonly route_id: string;
  /** Возвращает суммарный плановый объём по всем наряд-заданиям маршрута. */
  readonly volume_plan: number;
  /** Возвращает фактический перевезённый объём. */
  readonly volume_fact: number;
  /** Возвращает идентификатор секции. */
  readonly section_id?: number | null;
  /** Возвращает список техники на маршруте. */
  readonly vehicles?: readonly VehicleFleetControl[];
  /** Возвращает список идентификаторов наряд-заданий, составляющих этот маршрут.  */
  readonly route_task_ids?: readonly string[];
  /** Возвращает длину маршрута ПП→ПР по графу (метры). */
  readonly route_length_m?: number | null;
}

/** Представляет фильтры для запроса данных страницы "Управление техникой". */
export interface FleetControlQueryArgs {
  /** Возвращает фильтр по типу места. */
  readonly route_id?: readonly string[];
}

/** Представляет модель, получаемую по запросу "Управление техникой". */
export interface FleetControlResponse {
  /** Возвращает список маршрутов. */
  readonly routes?: readonly RouteFleetControl[];
  /** Возвращает список техники без активного задания. */
  readonly no_task?: readonly VehicleFleetControl[];
  /** Возвращает список гаражей (включая пустые) с техникой по каждому гаражу. */
  readonly garages?: readonly GarageFleetControl[];
  /** Возвращает список техники "В простое". */
  readonly idle?: readonly VehicleFleetControl[];
  /** Возвращает дату смены. */
  readonly shift_date?: string | null;
  /** Возвращает номер смены. */
  readonly shift_num?: number | null;
}

/** Представляет модель, получаемую по запросу маршрутов. */
export interface FleetControlRoutesResponse {
  /** Возвращает идентификатор маршрута. */
  readonly route_id: string;
  /** Возвращает идентификатор пункта погрузки. */
  readonly place_a_id: number;
  /** Возвращает идентификатор пункта разгрузки. */
  readonly place_b_id: number;
}

/** Представляет модель, получаемую по запросу информации о технике в контексте страницы "Управление техникой". */
export interface FleetControlVehicleTooltipResponse {
  /** Возвращает системное имя последнего статуса (state machine); при отсутствии данных — no_data. */
  readonly state: string;
  /** Возвращает длительность последнего статуса (сек;, null если статус не определён. */
  readonly state_duration?: number | null;
  /** Возвращает количество выполненных рейсов; null если не применимо. */
  readonly actual_trips_count?: number | null;
  /** Возвращает количество запланированных рейсов; null если не применимо. */
  readonly planned_trips_count?: number | null;
  /** Возвращает вес (tonnes) из telemetry-service; null если нет данных в стриме. */
  readonly weight?: number | null;
  /** Возвращает скорость (km/h) из telemetry-service; null если нет данных в стриме. */
  readonly speed?: number | null;
  /** Возвращает название места; null если нет данных. */
  readonly place_name?: string | null;
  /** Возвращает время последнего сообщения в стримах telemetry-service (gps, speed, weight), UTC в формате YYYY-MM-DDTHH:MM:SSZ (без дробной части секунд); null если нет данных. */
  readonly last_message_timestamp?: string | null;
}

/** Представляет модель, записи в сводке перевезённого объёма по видам груза за текущую смену. */
export interface ShiftLoadTypeVolumesItemResponse {
  /** Возвращает идентификатор вида груза. */
  readonly load_type_id: number;
  /** Возвращает наименование вида груза; пустая строка, если справочник не вернул имя. */
  readonly load_type_name: string;
  /** Возвращает объём (м³) по участкам: при переданных section_id — сумма по любому из участков (OR), иначе по всем. */
  readonly volume_sections_m3: number;
  /** Возвращает объём (м³) по местам разгрузки: при переданных place_id — сумма по любому из мест (OR), иначе по всем. */
  readonly volume_places_m3: number;
}

/** Представляет модель, сводки перевезённого объёма по видам груза за текущую смену. */
export interface ShiftLoadTypeVolumesResponse {
  /** Возвращает дату смены. */
  readonly shift_date: string | null;
  /** Возвращает номер смены. */
  readonly shift_num: number | null;
  /** Возвращает список записей в сводке. */
  readonly items: readonly ShiftLoadTypeVolumesItemResponse[];
}

/** Представляет фильтры сводки перевезённого объёма по видам груза за текущую смену. */
export interface ShiftLoadTypeVolumesQueryArgs {
  /** Возвращает фильтр по участкам. */
  readonly section_id?: readonly number[] | null;
  /** Возвращает фильтр по местам разгрузки. */
  readonly place_id?: readonly number[] | null;
}

/** Представляет модель, передаваемую при создании нового маршрута. */
export interface CreateRouteFleetControlRequest {
  /** Возвращает идентификатор места погрузки. */
  readonly place_a_id: number;
  /** Возвращает идентификатор места разгрузки. */
  readonly place_b_id: number;
}

/** Представляет модель, передаваемую при редактировании маршрута. */
export interface UpdateRouteFleetControlRequest {
  /** Возвращает идентификатор изначального места погрузки. */
  readonly from_place_a_id: number;
  /** Возвращает идентификатор изначального места разгрузки. */
  readonly from_place_b_id: number;
  /** Возвращает идентификатор назначаемого места погрузки. */
  readonly to_place_a_id: number;
  /** Возвращает идентификатор назначаемого места разгрузки. */
  readonly to_place_b_id: number;
}

/** Представляет модель, передаваемую для перемещения техники. */
export interface DispatcherAssignmentVehicleRequest {
  /** Возвращает идентификатор техники. */
  readonly vehicle_id: number;
  /** Возвращает тип текущего места назначения техники. */
  readonly source_kind: AssignPlaceType;
  /** Возвращает идентификатор текущего пункта погрузки. */
  readonly source_route_place_a_id: number | null;
  /** Возвращает идентификатор текущего пункта разгрузки. */
  readonly source_route_place_b_id: number | null;
  /** Возвращает идентификатор текущего гаража. */
  readonly source_garage_place_id: number | null;
  /** Возвращает тип места назначения техники для перемещения. */
  readonly target_kind: AssignPlaceType;
  /** Возвращает идентификатор пункта погрузки для перемещения. */
  readonly target_route_place_a_id: number | null;
  /** Возвращает идентификатор пункта разгрузки для перемещения. */
  readonly target_route_place_b_id: number | null;
  /** Возвращает идентификатор гаража для перемещения. */
  readonly target_garage_place_id: number | null;
}

/** Представляет модель, получаемую при создании нового маршрута. */
export interface FleetControlMutationResponse {
  /** Возвращает признак успеха/неудачи выполнения запроса. */
  readonly success: true;
  /** Возвращает сообщение от сервера. */
  readonly message: string;
}

/** Представляет модель черновика маршрута. */
export type RouteDraftFleetControl = Partial<RouteFleetControl> & Pick<RouteFleetControl, 'route_id'>;

/** Представляет модель сообщения, получаемую в стриме. */
export interface FleetControlRouteStreamMessage {
  /** Возвращает тип события. */
  readonly event_type: 'route_progress';
  /** Возвращает идентификатор оборудования. */
  readonly vehicle_id: number;
  /** Возвращает процент прогресса движения по маршруту. */
  readonly progress_percent: number;
  /** Возвращает признак движения оборудования вперед. */
  readonly is_moving_forward: boolean;
  /** Возвращает статус оборудования. */
  readonly state: string;
  /** Возвращает признак груженого оборудования. */
  readonly is_loaded: boolean;
}
