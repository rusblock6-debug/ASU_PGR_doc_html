import { type RefObject, useEffect } from 'react';

/**
 * Представляет хук для отслеживания кликов вне элемента.
 *
 * @param ref ссылка на элемент.
 * @param handler обработчик клика.
 * @param isActive признак активности хука.
 */
export function useClickOutside(ref: RefObject<HTMLElement | null>, handler: () => void, isActive = true) {
  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node) && isActive) {
        handler();
      }
    };

    document.addEventListener('click', handleClick);
    document.addEventListener('mousedown', handleClick);

    return () => {
      document.removeEventListener('click', handleClick);
      document.removeEventListener('mousedown', handleClick);
    };
  }, [ref, handler, isActive]);
}
