import type { EntityState } from '@reduxjs/toolkit';

import type { EquipmentModel } from '@/shared/api/endpoints/equipment-models';
import type { Pagination } from '@/shared/api/types';
import type { LocationModel } from '@/shared/models/LocationModel';

/**
 * Тип транспортного средства.
 *
 * `vehicle` — служебный тип из родительской таблицы БД.
 * Для него нет иконки и нет отображения на карте — в основном в UI оно не используется.
 * Типы, доступные пользователю, перечислены в {@link vehicleTypeOptions}.
 */
export type VehicleType = 'shas' | 'pdm' | 'vehicle';

/** Статус транспортного средства. */
export type VehicleStatus = 'active' | 'maintenance' | 'repair' | 'inactive';

/** Представляет транспортное средство. */
export interface Vehicle {
  /** Идентификатор техники. */
  readonly id: number;
  /** Идентификатор предприятия. */
  readonly enterprise_id: number;
  /** Тип техники (shas, pdm, vehicle). */
  readonly vehicle_type: VehicleType;
  /** Название техники (1-100 символов). */
  readonly name: string;
  /** Идентификатор модели. */
  readonly model_id: number | null;
  /** Модель техники. */
  readonly model: EquipmentModel | null;
  /** Серийный номер (до 100 символов). */
  readonly serial_number: string | null;
  /** Регистрационный номер (до 50 символов). */
  readonly registration_number: string | null;
  /** Статус техники. По умолчанию «active». */
  readonly status: VehicleStatus;
  /** Техника активна. По умолчанию true. */
  readonly is_active: boolean;
  /** Дата начала активности (формат date). */
  readonly active_from: string | null;
  /** Дата окончания активности (формат date). */
  readonly active_to: string | null;
  /** Время создания (формат date-time). */
  readonly created_at: string;
  /** Время обновления (формат date-time). */
  readonly updated_at: string;
}

/**
 * Представляет аргументы запроса списка транспортных средств
 */
export interface VehiclesQueryArg {
  /** Идентификатор предприятия. */
  readonly enterprise_id?: number;
  /** Тип техники. */
  readonly vehicle_type?: string;
}

/** Представляет ответ API со списком транспортных средств с пагинацией. */
export interface VehiclesResponse extends Pagination {
  /** Элементы на странице. */
  readonly items: readonly Vehicle[];
}

/** Нормализованный ответ списка транспортных средств */
export type NormalizedVehiclesResponse = Pagination & EntityState<Vehicle, number>;

/**
 * Представляет схему создания транспортного средства.
 */
export interface CreateVehicleRequest {
  /** Идентификатор предприятия. */
  readonly enterprise_id: number;
  /** Тип техники (shas, pdm, vehicle). */
  readonly vehicle_type: VehicleType;
  /** Название техники (1-100 символов). */
  readonly name: string;
  /** Идентификатор модели. */
  readonly model_id?: number | null;
  /** Серийный номер (до 100 символов). */
  readonly serial_number?: string | null;
  /** Регистрационный номер (до 50 символов). */
  readonly registration_number?: string | null;
  /** Статус техники. По умолчанию "active". */
  readonly status?: VehicleStatus;
  /** Техника активна. По умолчанию true. */
  readonly is_active?: boolean;
  /** Дата начала активности (формат date). */
  readonly active_from?: string | null;
  /** Дата окончания активности (формат date). */
  readonly active_to?: string | null;
}

/**
 * Представляет схему обновления транспортного средства.
 * Все поля опциональные — передавайте только те, которые нужно изменить.
 */
export interface UpdateVehicleRequest {
  /** Название техники (1-100 символов). */
  readonly name?: string | null;
  /** Идентификатор модели. */
  readonly model_id?: number | null;
  /** Серийный номер (до 100 символов). */
  readonly serial_number?: string | null;
  /** Регистрационный номер (до 50 символов). */
  readonly registration_number?: string | null;
  /** Статус техники. */
  readonly status?: VehicleStatus | null;
  /** Техника активна. */
  readonly is_active?: boolean | null;
  /** Дата начала активности (формат date). */
  readonly active_from?: string | null;
  /** Дата окончания активности (формат date). */
  readonly active_to?: string | null;
  /** Тип техники (shas, pdm, vehicle). */
  readonly vehicle_type?: VehicleType;
}

/** Представляет параметры обновления транспортного средства. */
export interface UpdateVehicleParams {
  /** Идентификатор транспортного средства. */
  readonly id: number;
  /** Тело запроса. */
  readonly body: UpdateVehicleRequest;
}

/** Представляет ответ со списком последних мест и горизонтов по подвижному оборудованию. */
export interface VehiclePlacesResponse {
  /** Список мест и горизонтов по подвижному оборудованию. */
  readonly items: readonly VehiclePlaceItem[];
}

/** Представляет элемент списка мест и горизонтов по подвижному оборудованию. */
export interface VehiclePlaceItem {
  /** Идентификатор горизонта. */
  readonly horizon_id: number;
  /** Идентификатор места. */
  readonly place_id: number;
  /** Идентификатор транспортного средства. */
  readonly vehicle_id: number;
}

/** Представляет модель ответа попапа транспортного средства на карте. */
export interface VehiclePopupResponse {
  /** Системное название статуса. */
  readonly status_system_name: string | null;
  /** Идентификатор места начала маршрута. */
  readonly place_start_id: number | null;
  /** Идентификатор места конца маршрута. */
  readonly place_finish_id: number | null;
  /** Плановое количество рейсов. */
  readonly planned_trips_count: number | null;
  /** Фактическое количество рейсов. */
  readonly actual_trips_count: number | null;
  /** Вес. */
  readonly weight: number | null;
  /** Скорость. */
  readonly speed: number | null;
  /** Идентификатор текущего местоположения. */
  readonly current_places_id: number | null;
}

/** Представляет ответ со списком состояний по подвижному оборудованию. */
export interface VehicleStateResponse {
  /** Список состояний по подвижному оборудованию. */
  readonly items: readonly VehicleStateItem[];
}

/** Представляет элемент списка состояний по подвижному оборудованию. */
export interface VehicleStateItem {
  /** Идентификатор транспортного средства. */
  readonly vehicle_id: number;
  /** Состояние. */
  readonly status: string;
}

/** Координаты транспорта из WebSocket-потока /ws/vehicle-tracking. */
export interface VehicleCoordinates extends LocationModel {
  /** Идентификатор транспортного средства. */
  readonly vehicle_id: number;
}

/** Элемент SSE-потока /stream/vehicles — текущее состояние машины. */
export interface VehicleStateEvent {
  /** Тип события. */
  readonly event_type: 'vehicle_state';
  /** Идентификатор транспортного средства. */
  readonly vehicle_id: number;
  /** Текущий статус машины. */
  readonly state: string | null;
  /** Идентификатор горизонта. */
  readonly horizon_id: number | null;
  /** Идентификатор последнего тега/места. */
  readonly place_id: number | null;
}
