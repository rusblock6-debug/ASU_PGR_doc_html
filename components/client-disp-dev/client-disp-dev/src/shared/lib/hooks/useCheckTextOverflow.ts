import { type Ref, useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';

/**
 * Хук для проверки полного отображения текста.
 */
export function useCheckTextOverflow<T extends HTMLElement>(
  text?: string | number | null | readonly string[],
  externalRef?: Ref<T>,
) {
  const innerRef = useRef<T>(null);

  const [isTextOverflowed, setIsTextOverflowed] = useState(false);

  const setRef = useCallback(
    (node: T | null) => {
      innerRef.current = node;

      if (!externalRef) return;

      if (typeof externalRef === 'function') {
        externalRef(node);
      } else {
        externalRef.current = node;
      }
    },
    [externalRef],
  );

  const checkOverflow = useCallback(() => {
    if (innerRef.current) {
      const element = innerRef.current;
      const isOverflowed = element.scrollWidth > element.clientWidth;
      setIsTextOverflowed(isOverflowed);
    }
  }, []);

  useLayoutEffect(() => {
    const frame = requestAnimationFrame(checkOverflow);
    return () => cancelAnimationFrame(frame);
  }, [text, checkOverflow]);

  useEffect(() => {
    if (!innerRef.current) return;

    const observer = new ResizeObserver(checkOverflow);
    observer.observe(innerRef.current);

    return () => observer.disconnect();
  }, [checkOverflow]);

  return { ref: setRef, isTextOverflowed };
}
