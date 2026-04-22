import { useThree } from '@react-three/fiber';
import type { RefObject } from 'react';
import { useEffect, useRef } from 'react';
import { Plane, Raycaster, Vector2, Vector3 } from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';

/** Параметры хука {@link usePlaneDrag}. */
interface UsePlaneDragOptions {
  /** Y-координата (высота) по которой двигается объект. */
  readonly y: number;
  /** `OrbitControls` для временного отключения панорамирования во время перемешения. */
  readonly controlsRef: RefObject<OrbitControlsImpl | null>;
  /** Вызывается при движении: передаёт id и новые `x/z` координаты. */
  readonly onMove: ((id: string, x: number, z: number) => void) | undefined;
  /** Вызывается, когда перетаскивание завершено. */
  readonly onDragEnd?: () => void;
  /**
   * Вызывается при каждом движении во время перетаскивания (через requestAnimationFrame).
   * Если передан `onMove` вызывается только в конце перетаскивания, когда отпустили ЛКМ.
   */
  readonly onDragProgress?: (id: string, x: number, z: number) => void;
}

/**
 * Хук для перетаскивания объекта по горизонтальной плоскости в сцене R3F.
 *
 * Хук проецирует (raycasting) курсор на невидимую горизонтальную плоскость на высоте `y`
 * и передаёт полученные координаты x/z через колбэки. Объект следует по этой плоскости вслед за курсором.
 *
 * В процессе перетаскивания панорамирование OrbitControls отключается автоматически, чтобы камера не следовала за объектом.
 * Обновления позиции троттлятся через `requestAnimationFrame` — срабатывают не чаще одного раза за кадр.
 */
export function usePlaneDrag({ y, controlsRef, onMove, onDragEnd, onDragProgress }: UsePlaneDragOptions) {
  const { camera, gl } = useThree();
  const dragIdRef = useRef<string | null>(null);
  const isDraggingRef = useRef(false);
  const pendingCoordsRef = useRef<{ clientX: number; clientY: number } | null>(null);
  const rafIdRef = useRef<number | null>(null);
  const lastHitRef = useRef<Vector3 | null>(null);

  useEffect(() => {
    if (!onMove) return;

    const raycaster = new Raycaster();
    const pointer = new Vector2();
    const intersection = new Vector3();
    const dragPlane = new Plane(new Vector3(0, 1, 0), -y);
    const domElement = gl.domElement;

    const raycast = (coords: { clientX: number; clientY: number }) => {
      const rect = domElement.getBoundingClientRect();
      pointer.x = ((coords.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((coords.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(pointer, camera);
      return raycaster.ray.intersectPlane(dragPlane, intersection) ? intersection : null;
    };

    const cancelPendingRaf = () => {
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = null;
      }
    };

    const flushMove = () => {
      rafIdRef.current = null;
      const coords = pendingCoordsRef.current;
      if (!coords || !dragIdRef.current) return;

      const hit = raycast(coords);
      if (hit) {
        if (onDragProgress) {
          onDragProgress(dragIdRef.current, hit.x, hit.z);
          lastHitRef.current = hit.clone();
        } else {
          onMove(dragIdRef.current, hit.x, hit.z);
        }
      }
      pendingCoordsRef.current = null;
    };

    const commitFinalPosition = () => {
      if (!onDragProgress) return;
      const hit = lastHitRef.current;
      if (hit && dragIdRef.current) {
        onMove(dragIdRef.current, hit.x, hit.z);
      }
      lastHitRef.current = null;
    };

    const handlePointerMove = (event: PointerEvent) => {
      if (!dragIdRef.current) return;

      pendingCoordsRef.current = { clientX: event.clientX, clientY: event.clientY };

      if (rafIdRef.current === null) {
        rafIdRef.current = requestAnimationFrame(flushMove);
      }
    };

    const handlePointerUp = () => {
      if (!dragIdRef.current) return;

      cancelPendingRaf();
      flushMove();
      commitFinalPosition();

      dragIdRef.current = null;
      isDraggingRef.current = false;
      if (controlsRef.current) {
        controlsRef.current.enablePan = true;
      }
      onDragEnd?.();
    };

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp);

    return () => {
      cancelPendingRaf();
      flushMove();
      commitFinalPosition();
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
  }, [y, camera, gl, controlsRef, onMove, onDragEnd, onDragProgress]);

  const startDrag = (id: string) => {
    dragIdRef.current = id;
    isDraggingRef.current = true;
    if (controlsRef.current) {
      controlsRef.current.enablePan = false;
    }
  };

  return { startDrag, isDraggingRef } as const;
}
