import { useLayoutEffect, useRef } from 'react';

import type { ElementCoordinates } from '@/shared/ui/types';

/**
 * Представляет хук для позиционирования элемента.
 *
 * @param coordinates координаты для позиционирования.
 * @param offsetX смещение по оси Х.
 * @param offsetY смещение по оси У.
 */
export function useElementPositioning(coordinates: ElementCoordinates, offsetX = 0, offsetY = 0) {
  const ref = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (!ref.current) return;

    const rect = ref.current.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    let top = coordinates.y + offsetY;
    let left = coordinates.x + offsetX;

    if (left + rect.width > vw) left = coordinates.x - rect.width - offsetX;
    if (top + rect.height > vh) top = coordinates.y - rect.height - offsetY;
    if (left < 0) left = offsetX;
    if (top < 0) top = offsetY;

    Object.assign(ref.current.style, {
      left: `${left}px`,
      top: `${top}px`,
    });
  }, [coordinates.x, coordinates.y, offsetX, offsetY]);

  return ref;
}
