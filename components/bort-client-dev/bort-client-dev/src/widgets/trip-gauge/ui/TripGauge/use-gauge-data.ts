import {
  ARC_DEGREES,
  describeRoundedRingPath,
  GAUGE_RADIUS,
  getPointOnCircle,
  getTickAngles,
  getTickLineCoords,
  MIN_VISUAL_SEGMENTS,
  START_ANGLE,
  TICK_COUNT,
  type Point,
  type TickCoords,
} from './gauge-geometry';

const GROUP_GAP_DEGREES = 2;

/** Данные для отрисовки дуги, тиков и стрелки спидометра. */
interface GaugeData {
  readonly displayActual: number;
  readonly displayPlanned: number;
  readonly filledPath: string | null;
  readonly unfilledPath: string | null;
  readonly ticks: TickCoords[];
  readonly pointer: { readonly center: Point; readonly rotation: number } | null;
}

/** Считает path SVG, тики и положение указателя по факту и плану рейсов. */
export const useGaugeData = (actual: number, planned: number) => {
  const normalizedPlanned = Math.max(0, Math.trunc(planned));
  const normalizedActual = Math.min(Math.max(0, Math.trunc(actual)), normalizedPlanned);

  const segmentCount = normalizedPlanned > 0 ? normalizedPlanned : MIN_VISUAL_SEGMENTS;
  const segmentActual = normalizedPlanned > 0 ? normalizedActual : 0;

  const segDeg = ARC_DEGREES / segmentCount;
  const boundaryAngle = START_ANGLE + segmentActual * segDeg;
  const hasBothGroups = segmentActual > 0 && segmentActual < segmentCount;
  const halfGap = hasBothGroups ? GROUP_GAP_DEGREES / 2 : 0;

  const filledPath = segmentActual > 0 ? describeRoundedRingPath(START_ANGLE, boundaryAngle - halfGap) : null;

  const unfilledPath =
    segmentActual < segmentCount ? describeRoundedRingPath(boundaryAngle + halfGap, START_ANGLE + ARC_DEGREES) : null;

  let pointer: GaugeData['pointer'] = null;
  let filledSpanDegrees = 0;

  if (segmentActual > 0) {
    filledSpanDegrees = boundaryAngle - halfGap - START_ANGLE;
    const lastSegCenter = START_ANGLE + (segmentActual - 0.5) * segDeg;

    pointer = {
      center: getPointOnCircle(GAUGE_RADIUS, lastSegCenter),
      rotation: lastSegCenter + 90,
    };
  }

  const tickCount = filledSpanDegrees > 0 ? Math.max(2, Math.round((TICK_COUNT * filledSpanDegrees) / ARC_DEGREES)) : 0;
  const tickAngles = getTickAngles(START_ANGLE, filledSpanDegrees, tickCount);
  const ticks = tickAngles.map(getTickLineCoords);

  return {
    displayActual: normalizedPlanned > 0 ? normalizedActual : 0,
    displayPlanned: normalizedPlanned,
    filledPath,
    unfilledPath,
    ticks,
    pointer,
  };
};
