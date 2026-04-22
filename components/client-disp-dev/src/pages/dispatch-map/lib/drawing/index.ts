export { CIRCLE_SEGMENTS, HORIZONTAL_ROTATION, INNER_CIRCLE_Z_OFFSET } from './model/constants';
export { buildEdgeSegments, buildSegments, isNearAnyPoint, isNearAnySegment, projectOnSegment } from './model/geometry';
export { calculateCumulativeDistances, formatDistance } from './model/distance';
export type { DragPosition, GhostPointInfo, MoveScenePoint, PolylinePoint, ScenePoint, Segment } from './model/types';
export { usePolylineDrawing } from './model/usePolylineDrawing';

export { useClickGuard } from './hooks/useClickGuard';
export { useCoordinatedDrag } from './hooks/useCoordinatedDrag';
export { usePlaneDrag } from './hooks/usePlaneDrag';

export { DragCoordinationProvider, useDragCoordinationContext } from './ui/DragCoordinationProvider';

export { CirclePoint } from './ui/CirclePoint';
export { PointInsertOverlay } from './ui/PointInsertOverlay';
export { BridgedHtml } from './ui/BridgedHtml';
export { BridgedSceneTooltip, SceneTooltip, TooltipButton } from './ui/SceneTooltip';
