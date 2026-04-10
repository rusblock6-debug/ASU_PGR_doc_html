import { useEffect } from 'react';

import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';

/**
 * Стрелки вверх/вниз и Enter дублируют on-screen kiosk-контролы.
 */
export const KioskKeyboardNav = () => {
  const { moveUp, moveDown, confirm, itemIds } = useKioskNavigation();

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target;
      if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) {
        return;
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault();
        moveUp();
        return;
      }
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        moveDown();
        return;
      }
      if (event.key === 'Enter' && itemIds.length > 0) {
        event.preventDefault();
        confirm();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [moveUp, moveDown, confirm, itemIds.length]);

  return null;
};
