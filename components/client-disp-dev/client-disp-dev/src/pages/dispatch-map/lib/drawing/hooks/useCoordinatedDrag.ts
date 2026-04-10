import type { MoveScenePoint } from '../model/types';
import { useDragCoordinationContext } from '../ui/DragCoordinationProvider';

import { usePlaneDrag } from './usePlaneDrag';

/** Параметры хука {@link useCoordinatedDrag}. */
interface UseCoordinatedDragOptions {
  /** Y-координата (высота) плоскости перетаскивания. */
  readonly y: number;
  /** Колбэк перемещения. При `deferMove` вызывается только при отпускании. */
  readonly onMove: MoveScenePoint | undefined;
  /** При `true` — dragPositionRef обновляется каждый кадр, `onMove` вызывается только при отпускании. */
  readonly deferMove?: boolean;
  /** Обработчик при начале перетаскивания. */
  readonly onDragStart?: () => void;
  /** Обработчик при окончании перетаскивания. */
  readonly onDragEnd?: () => void;
}

/**
 * Хук для координированного перетаскивания: обёртка над {@link usePlaneDrag}, интегрированная с {@link DragCoordinationProvider}.
 *
 * Записывает промежуточную позицию в `dragPositionRef` (при `deferMove`),
 * уведомляет о начале/конце перетаскивания через `notifyDragStart/notifyDragEnd`.
 */
export function useCoordinatedDrag({ y, onMove, deferMove, onDragStart, onDragEnd }: UseCoordinatedDragOptions) {
  const { controlsRef, dragPositionRef, isDragging, notifyDragStart, notifyDragEnd } = useDragCoordinationContext();

  const setDragPosition = (id: string, x: number, z: number) => {
    dragPositionRef.current = { id, x, z };
  };

  const handleDragEnd = () => {
    dragPositionRef.current = null;
    notifyDragEnd();
    onDragEnd?.();
  };

  const { startDrag: startPlaneDrag } = usePlaneDrag({
    y,
    controlsRef,
    onMove,
    onDragProgress: deferMove ? setDragPosition : undefined,
    onDragEnd: handleDragEnd,
  });

  const startDrag = (id: string) => {
    startPlaneDrag(id);
    notifyDragStart();
    onDragStart?.();
  };

  return { startDrag, dragPositionRef, isDragging };
}
