import { type Ref, useEffect, useRef, useState } from 'react';

/**
 * Хук для проверки полного отображения текста.
 */
export function useCheckTextOverflow<T extends HTMLElement>(
  text?: string | number | null | readonly string[],
  externalRef?: Ref<T>,
) {
  const innerRef = useRef<T>(null);

  const [isTextOverflowed, setIsTextOverflowed] = useState(false);

  const setRef = (node: T | null) => {
    innerRef.current = node;

    if (!externalRef) return;

    if (typeof externalRef === 'function') {
      externalRef(node);
    } else {
      externalRef.current = node;
    }
  };

  useEffect(() => {
    const el = innerRef.current;
    if (!el) return;

    const run = () => {
      const isOverflowed = el.scrollWidth > el.clientWidth;
      setIsTextOverflowed(isOverflowed);
    };

    run();

    const observer = new ResizeObserver(run);
    observer.observe(el);

    return () => observer.disconnect();
  }, [text]);

  return { ref: setRef, isTextOverflowed };
}
