import { type RefObject, useEffect } from 'react';

/**
 * Представляет хук для отслеживания скролла вне элемента.
 *
 * @param ref ссылка на элемент.
 * @param handler обработчик скролла.
 * @param isActive признак активности хука.
 */
export function useOutsideScroll(ref: RefObject<HTMLElement | null>, handler: () => void, isActive = true) {
  useEffect(() => {
    const handleScroll = (event: Event) => {
      if (ref.current && !ref.current.contains(event.target as Node) && isActive) {
        handler();
      }
    };

    document.addEventListener('scroll', handleScroll, { capture: true });

    return () => {
      document.removeEventListener('scroll', handleScroll, { capture: true });
    };
  }, [ref, handler, isActive]);
}
