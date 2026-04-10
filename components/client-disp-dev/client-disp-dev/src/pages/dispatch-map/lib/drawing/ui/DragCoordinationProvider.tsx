import type { PropsWithChildren, RefObject } from 'react';
import { createContext, use, useRef } from 'react';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';

import type { DragPosition } from '../model/types';

/**
 * Значение контекста состояния перетаскивания между компонентами одного слоя.
 */
interface DragCoordinationValue {
  /** Ref на OrbitControls — блокируется во время перетаскивания. */
  readonly controlsRef: RefObject<OrbitControlsImpl | null>;
  /** Ref с позицией перетаскиваемого элемента для императивного обновления (ребра, узлы). */
  readonly dragPositionRef: RefObject<DragPosition | null>;
  /** Возвращает `true`, если любой компонент внутри провайдера сейчас перетаскивает элемент. */
  readonly isDragging: () => boolean;
  /** Уведомляет о начале перетаскивания. */
  readonly notifyDragStart: () => void;
  /** Уведомляет об окончании перетаскивания. */
  readonly notifyDragEnd: () => void;
}

const DragCoordinationContext = createContext<DragCoordinationValue | null>(null);

/**
 * Представляет свойства компонента {@link DragCoordinationProvider}.
 */
interface DragCoordinationProviderProps extends PropsWithChildren {
  /** Ref на OrbitControls — прокидывается из родительского контекста камеры. */
  readonly controlsRef: RefObject<OrbitControlsImpl | null>;
}

/**
 * Провайдер для хранения состояния перетаскивания для группы компонентов одного слоя.
 *
 * Хранит в контексте `dragPositionRef` — текущую промежуточную позицию при `deferMove`,
 * `isDragging` и нотификации старта/финиша, `controlsRef` — чтобы временно отключать панорамирование.
 */
export function DragCoordinationProvider({ controlsRef, children }: DragCoordinationProviderProps) {
  const dragPositionRef = useRef<DragPosition | null>(null);
  const isDraggingRef = useRef(false);

  const value = useRef<DragCoordinationValue>({
    controlsRef,
    dragPositionRef,
    isDragging: () => isDraggingRef.current,
    notifyDragStart: () => {
      isDraggingRef.current = true;
    },
    notifyDragEnd: () => {
      isDraggingRef.current = false;
    },
  }).current;

  return <DragCoordinationContext value={value}>{children}</DragCoordinationContext>;
}

/**
 * Хук для доступа к состоянию перетаскивания внутри {@link DragCoordinationProvider}.
 */
export function useDragCoordinationContext() {
  const context = use(DragCoordinationContext);
  if (!context) throw new Error('useDragCoordinationContext must be used within DragCoordinationProvider');

  return context;
}
