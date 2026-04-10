import { fromScene } from '../../coordinates';

import type { ScenePoint } from './types';

const EARTH_RADIUS_M = 6_371_000;
const DEG_TO_RAD = Math.PI / 180;

/**
 * Считает расстояние от первой точки до каждой следующей (в метрах).
 * Например: `[0, 12.4, 27.9, ...]`.
 * Для пустого списка точек возвращает `[0]`.
 */
export function calculateCumulativeDistances(points: readonly ScenePoint[]) {
  return points.slice(1).reduce(
    (distances, point, index) => {
      const prev = fromScene(points[index].x, points[index].z);
      const current = fromScene(point.x, point.z);
      const segmentDistance = calculateGeoDistance(prev.lon, prev.lat, current.lon, current.lat);

      distances.push(distances[index] + segmentDistance);
      return distances;
    },
    [0],
  );
}

/**
 * Приблизительное расстояние между двумя geo-координатами в метрах.
 *
 * Использует Equirectangular-аппроксимацию — достаточная точность
 * для масштабов карьера (погрешность < 0.1% на расстояниях до 10 км).
 *
 * @see https://www.movable-type.co.uk/scripts/latlong.html
 * @see https://en.wikipedia.org/wiki/Equirectangular_projection
 */
function calculateGeoDistance(lon1: number, lat1: number, lon2: number, lat2: number) {
  const dLat = (lat2 - lat1) * DEG_TO_RAD;
  const dLon = (lon2 - lon1) * DEG_TO_RAD;
  const avgLat = ((lat1 + lat2) / 2) * DEG_TO_RAD;
  const x = dLon * Math.cos(avgLat);
  return Math.sqrt(x * x + dLat * dLat) * EARTH_RADIUS_M;
}

/**
 * Преобразует расстояние в строку.
 * До 1000 м показывает метры без дробной части (123 м),
 * от 1000 м километры с двумя знаками после запятой (1.23 км).
 */
export function formatDistance(meters: number) {
  if (meters < 1000) {
    return `${Math.round(meters)} м`;
  }
  return `${(meters / 1000).toFixed(2)} км`;
}
