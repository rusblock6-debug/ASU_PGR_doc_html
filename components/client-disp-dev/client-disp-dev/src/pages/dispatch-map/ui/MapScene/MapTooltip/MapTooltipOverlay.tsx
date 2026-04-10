import { flip, offset, shift, useFloating } from '@floating-ui/react';
import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

import { useTooltipContent } from '../../../lib/tooltip-store';

import styles from './MapTooltipOverlay.module.css';

/**
 * Портал для тултипа, который следует за курсором мыши на карте.
 * Контент берётся из tooltip-store (общий для R3F и DOM),
 * позиционирование — через floating-ui, рендер через портал в document.body.
 */
export function MapTooltipOverlay() {
  const content = useTooltipContent();

  const { refs, floatingStyles } = useFloating({
    open: true,
    strategy: 'fixed',
    placement: 'right-start',
    middleware: [offset(14), flip(), shift({ padding: 8 })],
  });

  const mouseRef = useRef({ x: 0, y: 0 });
  const rafRef = useRef(0);

  useEffect(() => {
    const { x, y } = mouseRef.current;
    refs.setReference(createVirtualRef(x, y));

    const handleMove = (e: PointerEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };

      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        const pos = mouseRef.current;
        refs.setReference(createVirtualRef(pos.x, pos.y));
      });
    };

    document.addEventListener('pointermove', handleMove, { passive: true });
    return () => {
      document.removeEventListener('pointermove', handleMove);
      cancelAnimationFrame(rafRef.current);
    };
  }, [refs]);

  return createPortal(
    <div
      ref={refs.setFloating}
      className={styles.floating}
      style={floatingStyles}
    >
      {content}
    </div>,
    document.body,
  );
}

/**
 * Создаёт «невидимый» элемент-якорь в позиции курсора, к которому floating-ui привязывает тултип.
 */
function createVirtualRef(x: number, y: number) {
  return {
    getBoundingClientRect: () => DOMRect.fromRect({ x, y, width: 0, height: 0 }),
  };
}
