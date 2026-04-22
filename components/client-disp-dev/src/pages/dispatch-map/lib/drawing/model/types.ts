/** Точка с идентификатором в координатах сцены. */
export interface PolylinePoint extends ScenePoint {
  /** Уникальный идентификатор точки. */
  readonly id: string;
}

/** Результат расчёта ghost-точки на сегменте. */
export interface GhostPointInfo extends ScenePoint {
  /** Идентификатор сегмента, к которому привязана ghost-точка. */
  readonly segmentId: string;
}

/** Точка в плоскости карты (координаты сцены X/Z). */
export interface ScenePoint {
  /** Координата по оси X в сцене. */
  readonly x: number;
  /** Координата по оси Z в сцене. */
  readonly z: number;
}

/** Отрезок в координатах сцены, используемый для hit-тестов и ghost-точек. */
export interface Segment {
  /** Идентификатор сегмента. */
  readonly id: string;
  /** X-координата начала сегмента. */
  readonly ax: number;
  /** Z-координата начала сегмента. */
  readonly az: number;
  /** X-координата конца сегмента. */
  readonly bx: number;
  /** Z-координата конца сегмента. */
  readonly bz: number;
}

/** Позиция перетаскиваемого элемента (для императивного обновления связанных компонентов). */
export interface DragPosition extends ScenePoint {
  readonly id: string;
}

/** Унифицированный обработчик перемещения точки/узла по плоскости. */
/** Идентификатор перемещаемой сущности, новые координаты x и z. */
export type MoveScenePoint = (id: string, x: number, z: number) => void;
