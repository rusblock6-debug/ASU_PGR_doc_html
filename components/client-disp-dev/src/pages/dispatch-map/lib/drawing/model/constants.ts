import type { EulerTuple } from 'three';

/** Поворот плоскости из XY в XZ (горизонтальная ориентация на карте). */
export const HORIZONTAL_ROTATION = [-Math.PI / 2, 0, 0] as const satisfies EulerTuple;

/** Количество сегментов окружности (визуально гладкая окружность). */
export const CIRCLE_SEGMENTS = 24;

/** Z-смещение внутреннего круга для корректного наложения поверх обводки. */
export const INNER_CIRCLE_Z_OFFSET = 0.001;
