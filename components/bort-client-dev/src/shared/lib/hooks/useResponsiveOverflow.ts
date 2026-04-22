import { useLayoutEffect, useRef, useState } from 'react';

/**
 * Хук для адаптивного отображения DOM-элементов.
 */
export function useResponsiveOverflow() {
  const containerRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [hiddenCount, setHiddenCount] = useState(0);

  const calculate = () => {
    const container = containerRef.current;
    if (!container) return;

    const items = itemRefs.current;

    items.forEach((item) => {
      if (item) {
        item.style.display = '';
      }
    });

    let count = 0;

    items.forEach((ref) => {
      if (!ref) return;
      if (container.scrollWidth <= container.clientWidth) return;

      ref.style.display = 'none';
      count++;
    });

    setHiddenCount(count);
  };

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    calculate();
    const observer = new ResizeObserver(calculate);

    observer.observe(container);

    return () => {
      observer.disconnect();
    };
  }, []);

  const setItemRef = (el: HTMLDivElement | null, index: number) => {
    itemRefs.current[index] = el;
    if (el) {
      calculate();
    }
  };

  return {
    containerRef,
    itemRefs,
    setItemRef,
    hiddenCount,
  };
}
