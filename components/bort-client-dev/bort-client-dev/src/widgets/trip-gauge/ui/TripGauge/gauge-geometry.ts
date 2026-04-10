export const GAUGE_RADIUS = 170;
export const STROKE_WIDTH = 40;
export const ARC_DEGREES = 180;
export const START_ANGLE = 270 - ARC_DEGREES / 2;
export const TICK_INNER_RADIUS = 195;
export const TICK_OUTER_RADIUS = 200;
export const TICK_COUNT = 100;
/** При отсутствии плана показываем сетку из 8 сегментов (макет). */
export const MIN_VISUAL_SEGMENTS = 8;

export const POINTER_WIDTH = 44;
export const POINTER_HEIGHT = 18;

const BASE_GAP_DEGREES = 2;
const SVG_CENTER = 150;

/** Границы одного сегмента дуги (в градусах). */
export interface SegmentAngles {
  readonly startAngle: number;
  readonly endAngle: number;
}

/** Точка в координатах SVG viewBox спидометра. */
export interface Point {
  readonly x: number;
  readonly y: number;
}

/** Концы отрезка тика (inner → outer). */
export interface TickCoords {
  readonly x1: number;
  readonly y1: number;
  readonly x2: number;
  readonly y2: number;
}

const toRadians = (degrees: number) => (degrees * Math.PI) / 180;

/** Координаты точки на окружности с центром (SVG_CENTER, SVG_CENTER). */
export const getPointOnCircle = (radius: number, angle: number) => ({
  x: SVG_CENTER + radius * Math.cos(toRadians(angle)),
  y: SVG_CENTER + radius * Math.sin(toRadians(angle)),
});

/** SVG `path.d` для дуги окружности. */
export const describeArcPath = (radius: number, startAngle: number, endAngle: number) => {
  const start = getPointOnCircle(radius, startAngle);
  const end = getPointOnCircle(radius, endAngle);
  const largeArcFlag = Math.abs(endAngle - startAngle) > 180 ? 1 : 0;

  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${end.x} ${end.y}`;
};

/** Делит дугу на `count` сегментов с зазорами между ними. */
export const buildSegmentAngles = (count: number) => {
  if (count <= 0) return [];

  const totalGaps = BASE_GAP_DEGREES * (count - 1);
  const segmentDegrees = (ARC_DEGREES - totalGaps) / count;
  const segments: SegmentAngles[] = [];

  let cursor = START_ANGLE;
  for (let i = 0; i < count; i += 1) {
    segments.push({ startAngle: cursor, endAngle: cursor + segmentDegrees });
    cursor += segmentDegrees + BASE_GAP_DEGREES;
  }

  return segments;
};

/** Углы равномерно распределённых тиков вдоль дуги. */
export const getTickAngles = (startAngle: number, spanDegrees: number, count: number) => {
  if (count <= 0) return [];
  if (count === 1) return [startAngle + spanDegrees / 2];

  return Array.from({ length: count }, (_, i) => startAngle + (spanDegrees * i) / (count - 1));
};

const TRACK_CORNER_RADIUS = 10;
const RAD_TO_DEG = 180 / Math.PI;

/**
 * Замкнутый path кольцевого сектора со скруглёнными торцами.
 * Отрисовывается через fill, а не stroke.
 * Corner-radius автоматически уменьшается для узких сегментов.
 */
export const describeRoundedRingPath = (startAngle: number, endAngle: number) => {
  const innerR = GAUGE_RADIUS - STROKE_WIDTH / 2;
  const outerR = GAUGE_RADIUS + STROKE_WIDTH / 2;

  const spanDeg = endAngle - startAngle;
  const maxCornerRadius = (spanDeg / 3) * (Math.PI / 180) * innerR;
  const r = Math.min(TRACK_CORNER_RADIUS, Math.max(0, maxCornerRadius));

  const dInner = (r / innerR) * RAD_TO_DEG;
  const dOuter = (r / outerR) * RAD_TO_DEG;

  const p1 = getPointOnCircle(innerR, startAngle + dInner);
  const p2 = getPointOnCircle(innerR, endAngle - dInner);
  const p3 = getPointOnCircle(innerR + r, endAngle);
  const p4 = getPointOnCircle(outerR - r, endAngle);
  const p5 = getPointOnCircle(outerR, endAngle - dOuter);
  const p6 = getPointOnCircle(outerR, startAngle + dOuter);
  const p7 = getPointOnCircle(outerR - r, startAngle);
  const p8 = getPointOnCircle(innerR + r, startAngle);

  const innerLarge = endAngle - startAngle - 2 * dInner > 180 ? 1 : 0;
  const outerLarge = endAngle - startAngle - 2 * dOuter > 180 ? 1 : 0;

  return [
    `M ${p1.x} ${p1.y}`,
    `A ${innerR} ${innerR} 0 ${innerLarge} 1 ${p2.x} ${p2.y}`,
    `A ${r} ${r} 0 0 0 ${p3.x} ${p3.y}`,
    `L ${p4.x} ${p4.y}`,
    `A ${r} ${r} 0 0 0 ${p5.x} ${p5.y}`,
    `A ${outerR} ${outerR} 0 ${outerLarge} 0 ${p6.x} ${p6.y}`,
    `A ${r} ${r} 0 0 0 ${p7.x} ${p7.y}`,
    `L ${p8.x} ${p8.y}`,
    `A ${r} ${r} 0 0 0 ${p1.x} ${p1.y}`,
    'Z',
  ].join(' ');
};

/** Координаты линии тика (от inner до outer радиуса). */
export const getTickLineCoords = (angle: number) => {
  const p1 = getPointOnCircle(TICK_INNER_RADIUS, angle);
  const p2 = getPointOnCircle(TICK_OUTER_RADIUS, angle);

  return { x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y };
};
