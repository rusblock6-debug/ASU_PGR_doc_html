import type { ThreeEvent } from '@react-three/fiber';
import { useRef } from 'react';

/**
 * Порог смещения курсора (в пикселях), при котором взаимодействие
 * всё ещё считается кликом, а не началом перемещения.
 */
const DEFAULT_THRESHOLD_PX = 5;

/**
 * Хук для разделения клика и перемещения в 3D-сцене.
 *
 * Сохраняет координаты `pointerdown` (только для левой кнопки мыши),
 * а при `click` проверяет, что смещение не превышает `thresholdPx`.
 *
 * @param thresholdPx Максимально допустимое смещение курсора между `pointerdown` и `click`.
 * @returns Обработчик `pointerdown` и функцию-предикат для проверки клика.
 */
export function useClickGuard(thresholdPx = DEFAULT_THRESHOLD_PX) {
  const pointerDownRef = useRef<{ x: number; y: number } | null>(null);

  const handlePointerDown = (event: ThreeEvent<PointerEvent>) => {
    if (event.button !== 0) return;
    pointerDownRef.current = { x: event.nativeEvent.clientX, y: event.nativeEvent.clientY };
  };

  const isClick = (event: ThreeEvent<MouseEvent>) => {
    const start = pointerDownRef.current;
    pointerDownRef.current = null;
    if (!start) return false;

    const dx = event.nativeEvent.clientX - start.x;
    const dy = event.nativeEvent.clientY - start.y;
    return dx * dx + dy * dy <= thresholdPx * thresholdPx;
  };

  return { handlePointerDown, isClick };
}
