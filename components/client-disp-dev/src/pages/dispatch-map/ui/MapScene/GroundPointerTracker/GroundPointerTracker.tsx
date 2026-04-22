import { useThree } from '@react-three/fiber';
import { useEffect, useRef } from 'react';
import { Plane, Raycaster, Vector2, Vector3 } from 'three';

import { useGroundPointerContext } from '../../GroundPointerProvider';

/** Горизонтальная плоскость Y=0, по которой вычисляется пересечение луча от курсора. */
const GROUND = new Plane(new Vector3(0, 1, 0), 0);

/** Максимальное абсолютное значение X/Z — точки за пределами отбрасываются как невалидные. */
const MAX_COORDINATE = 5_000;

/**
 * Преобразует позицию курсора на экране в координаты на плоскости (плоскость Y=0).
 *
 * Слушает `window.pointermove` — срабатывает всегда, даже когда курсор над маркерами или попапами.
 * Это нужно чтобы не было проблем с определением координат при наведении.
 *
 * Результат записывается в ref'ы из {@link useGroundPointerContext}:
 * `pointerRef` (Vector3) и DOM-элементы `xRef`/`yRef` для отображения координат.
 */
export function GroundPointerTracker() {
  const { camera, gl } = useThree();
  const { pointerRef, xRef, yRef } = useGroundPointerContext();
  const animationId = useRef(0);

  useEffect(() => {
    const raycaster = new Raycaster();
    const normalizedPointer = new Vector2();
    const groundPoint = new Vector3();
    const element = gl.domElement;

    const handle = (event: PointerEvent) => {
      cancelAnimationFrame(animationId.current);
      animationId.current = requestAnimationFrame(() => {
        const rect = element.getBoundingClientRect();

        const isOutsideCanvas =
          event.clientX < rect.left ||
          event.clientX > rect.right ||
          event.clientY < rect.top ||
          event.clientY > rect.bottom;

        if (isOutsideCanvas) return;

        // Пиксельные координаты мыши → [-1, 1] для raycaster (Y инвертирован: в браузере вниз, в normalizedPointer — вверх)
        normalizedPointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        normalizedPointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(normalizedPointer, camera);

        if (raycaster.ray.intersectPlane(GROUND, groundPoint)) {
          if (Math.abs(groundPoint.x) > MAX_COORDINATE || Math.abs(groundPoint.z) > MAX_COORDINATE) return;

          pointerRef.current.copy(groundPoint);

          if (xRef.current) xRef.current.textContent = String(Math.round(groundPoint.x));
          if (yRef.current) yRef.current.textContent = String(Math.round(groundPoint.z));
        }
      });
    };

    window.addEventListener('pointermove', handle);

    return () => {
      cancelAnimationFrame(animationId.current);
      window.removeEventListener('pointermove', handle);
    };
  }, [camera, gl, pointerRef, xRef, yRef]);

  return null;
}
