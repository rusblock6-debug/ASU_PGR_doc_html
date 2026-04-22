/** Представляет модель данных для перемещения машины в определенное место на карте. */
export interface MoveVehicleRequest {
  /** Возвращает идентификатор места. */
  readonly place_id: number;
  /** Возвращает идентификатор машины. */
  readonly vehicle_id: number;
}
