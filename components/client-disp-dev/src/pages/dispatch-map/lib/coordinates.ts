import type { Vector3Tuple } from 'three';

import type { LocationModel } from '@/shared/models/LocationModel';

/** Коэффициент перевода градусов в радианы: `1° = π / 180 рад`. */
const DEG_TO_RAD = Math.PI / 180;

/**
 * Сколько единиц 3D-сцены приходится на 1 градус долготы.
 *
 * Например, если два объекта разнесены на 1 градус по долготе,
 * в сцене между ними будет указанное значение единиц по оси X.
 */
export const SCALE = 50_000;

/**
 * Фиксированный центр сцены — точка на карте, которая
 * в 3D-сцене отображается в начало координат `(0, 0, 0)`.
 *
 * Все остальные точки вычисляются как смещение относительно этого центра.
 */
export const DEFAULT_CENTER = {
  LONGITUDE: 59.81663427284831,
  LATITUDE: 58.172761974086455,
} as const;

/**
 * Коэффициент перевода метров в единицы 3D-сцены.
 *
 * Вычисляется на широте {@link DEFAULT_CENTER}: 1° долготы ≈ 111 320 · cos(lat) метров,
 * а {@link SCALE} задаёт, сколько scene-единиц в 1°.
 */
export const METERS_TO_SCENE = SCALE / (111_320 * Math.cos(DEFAULT_CENTER.LATITUDE * DEG_TO_RAD));

/**
 * Масштабный коэффициент для проекции Меркатора.
 *
 * Проекция Меркатора работает в радианах, а нам нужны единицы сцены.
 * Делим {@link SCALE} на {@link DEG_TO_RAD}, чтобы 1 градус долготы
 * в Меркаторе давал те же единицы, что и по оси X.
 * Это обеспечивает одинаковый масштаб по обеим осям — без этого
 * карта бы растягивалась или сжималась.
 */
const MERCATOR_SCALE = SCALE / DEG_TO_RAD;

/**
 * Проекция Меркатора для широты центра сцены, предвычисленная при загрузке.
 *
 * Чтобы не считать `latToMercatorY(DEFAULT_CENTER.LATITUDE)` каждый раз
 * при вызове {@link toScene} / {@link fromScene}, результат кешируется сюда.
 */
const CENTER_MERCATOR_Y = Math.log(Math.tan(Math.PI / 4 + (DEFAULT_CENTER.LATITUDE * DEG_TO_RAD) / 2));

/**
 * Переводит широту (градусы) в «Mercator Y».
 *
 * На обычной карте 1 градус широты выглядит одинаково везде.
 * Но в проекции Меркатора (Google Maps, Яндекс.Карты, Leaflet)
 * расстояния по вертикали растягиваются ближе к полюсам,
 * чтобы формы объектов на карте не искажались.
 *
 * Эта функция выполняет такое растяжение:
 * принимает обычную широту и возвращает координату по оси Y,
 * готовую для отображения на Меркаторной карте.
 *
 * @see https://habr.com/ru/companies/megafon/articles/964796/
 */
function latToMercatorY(latDeg: number) {
  return Math.log(Math.tan(Math.PI / 4 + (latDeg * DEG_TO_RAD) / 2));
}

/**
 * Обратная операция к {@link latToMercatorY}:
 * переводит «Mercator Y» обратно в обычную широту (градусы).
 *
 * Используется, когда нужно из координат 3D-сцены получить
 * реальные GPS-координаты (например, при клике по карте).
 */
function mercatorYToLat(mercY: number) {
  return (2 * Math.atan(Math.exp(mercY)) - Math.PI / 2) / DEG_TO_RAD;
}

/**
 * Переводит географические координаты (долгота, широта) в координаты 3D-сцены.
 *
 * Как это работает:
 * 1. Берём разницу между переданной точкой и фиксированным центром карты ({@link DEFAULT_CENTER}).
 * 2. Умножаем на масштаб, чтобы получить позицию в единицах сцены.
 *
 * Маппинг осей:
 * - Долгота (lon) → X: восток — положительный X.
 * - Широта (lat) → Z: север — отрицательный Z (чтобы «вверх» на экране был севером).
 *   Широта преобразуется через проекцию Меркатора ({@link latToMercatorY}),
 *   чтобы 3D-сцена совпадала с тайловой подложкой (Leaflet).
 * - Высота → Y: вверх — положительный Y.
 *
 * @param lon Долгота в градусах (например, `59.816`).
 * @param lat Широта в градусах (например, `58.173`).
 * @param y Высота объекта в сцене (0 = на земле).
 * @returns `[x, y, z]` — позиция в 3D-сцене.
 */
export function toScene(lon: number, lat: number, y = 0): Vector3Tuple {
  return [(lon - DEFAULT_CENTER.LONGITUDE) * SCALE, y, -(latToMercatorY(lat) - CENTER_MERCATOR_Y) * MERCATOR_SCALE];
}

/**
 * Обратная операция к {@link toScene}:
 * переводит координаты 3D-сцены обратно в географические координаты.
 *
 * @param sceneX Координата X в сцене (долгота после {@link toScene}).
 * @param sceneZ Координата Z в сцене (широта после {@link toScene}).
 * @returns Объект `{ lon, lat }` с географическими координатами.
 */
export function fromScene(sceneX: number, sceneZ: number): LocationModel {
  return {
    lon: sceneX / SCALE + DEFAULT_CENTER.LONGITUDE,
    lat: mercatorYToLat(-(sceneZ / MERCATOR_SCALE) + CENTER_MERCATOR_Y),
  };
}
