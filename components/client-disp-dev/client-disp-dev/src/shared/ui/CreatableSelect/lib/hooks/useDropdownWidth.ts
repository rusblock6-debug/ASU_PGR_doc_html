import type { RefObject } from 'react';
import { useEffect } from 'react';

/** Значения по умолчанию для CSS-переменных (в пикселях) */
const DEFAULT_LABEL_WIDTH = 200;
const DEFAULT_COLUMN_GAP = 16;

/**
 * Хук для установки CSS-переменной --dropdown-width
 * Используется для ограничения max-width текста в опциях
 */
export function useDropdownWidth(rootRef: RefObject<HTMLDivElement | null>) {
  useEffect(() => {
    if (!rootRef.current) return;

    const updateWidth = () => {
      const root = rootRef.current;
      if (!root) return;

      const style = getComputedStyle(root);
      const rootWidth = root.offsetWidth;
      const labelWidth = parseInt(style.getPropertyValue('--label-width'), 10) || DEFAULT_LABEL_WIDTH;
      const columnGap = parseInt(style.getPropertyValue('--column-gap'), 10) || DEFAULT_COLUMN_GAP;
      const calculatedWidth = rootWidth - labelWidth - columnGap;

      root.style.setProperty('--dropdown-width', `${calculatedWidth}px`);
    };

    updateWidth();

    const resizeObserver = new ResizeObserver(updateWidth);
    resizeObserver.observe(rootRef.current);

    return () => resizeObserver.disconnect();
    // rootRef — стабильный объект, не нужен в зависимостях
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
