import type { Pagination } from '@/shared/api/types';

/** Представляет модель оборудования. */
export interface EquipmentModel extends EquipmentModelSpecs {
  /** Возвращает ID модели оборудования. */
  readonly id: number;
  /** Возвращает имя модели. */
  readonly name: string;
  /** Возвращает время создания. */
  readonly created_at: string;
  /** Возвращает время обновления. */
  readonly updated_at: string;
}

/** Представляет технические характеристики модели оборудования. */
export interface EquipmentModelSpecs {
  /** Возвращает максимальную скорость. */
  readonly max_speed: number | null;
  /** Возвращает объём бака. */
  readonly tank_volume: number | null;
  /** Возвращает грузоподъёмность. */
  readonly load_capacity_tons: number | null;
  /** Возвращает объём кузова/ковша. */
  readonly volume_m3: number | null;
}

/** Представляет аргументы запроса списка моделей оборудования. */
export interface EquipmentModelsQueryArg {
  /** Поиск по подстроке в названии модели (регистронезависимый). */
  readonly consist?: string;
}

/** Представляет ответ API со списком моделей оборудования. */
export interface EquipmentModelsApiResponse extends Pagination {
  items: readonly EquipmentModel[];
}

/** Представляет запрос на создание модели оборудования. */
export interface CreateEquipmentModelRequest {
  /** Название модели. */
  readonly name: string;
  /** Максимальная скорость. */
  readonly max_speed?: number | null;
  /** Объём бака. */
  readonly tank_volume?: number | null;
  /** Грузоподъёмность. */
  readonly load_capacity_tons?: number | null;
  /** Объём кузова/ковша. */
  readonly volume_m3?: number | null;
}

/** Представляет запрос на обновление модели оборудования. */
export type UpdateEquipmentModelRequest = Partial<CreateEquipmentModelRequest>;

/** Представляет параметры обновления модели оборудования. */
export interface UpdateEquipmentModelParams {
  /** Идентификатор модели. */
  readonly id: number;
  /** Тело запроса. */
  readonly body: UpdateEquipmentModelRequest;
}
