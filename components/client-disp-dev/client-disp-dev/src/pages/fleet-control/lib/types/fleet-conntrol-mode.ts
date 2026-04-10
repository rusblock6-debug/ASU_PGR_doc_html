/**
 * Режимы отображения страницы "Управление техникой".
 */
export const FLEET_CONTROL_MODE = {
  /** Горизонтальный режим. */
  HORIZONTAL: 'horizontal',
  /** Вертикальный режим. */
  VERTICAL: 'vertical',
} as const;

/**
 * Представляет типы режимов отображения страницы "Управление техникой".
 */
export type FleetControlMode = (typeof FLEET_CONTROL_MODE)[keyof typeof FLEET_CONTROL_MODE];
