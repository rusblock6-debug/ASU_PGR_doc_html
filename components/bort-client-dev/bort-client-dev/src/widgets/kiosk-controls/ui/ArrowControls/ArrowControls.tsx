import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';

import styles from './ArrowControls.module.css';

/**
 * Вертикальные кнопки вверх/вниз для перемещения фокуса по списку.
 */
export const ArrowControls = () => {
  const { moveUp, moveDown, itemIds } = useKioskNavigation();
  const disabled = itemIds.length === 0;

  return (
    <div
      className={styles.stack}
      role="group"
      aria-label="Навигация по списку"
    >
      <button
        type="button"
        className={styles.button}
        aria-label="Предыдущий элемент"
        disabled={disabled}
        onClick={moveUp}
      >
        ↑
      </button>
      <button
        type="button"
        className={styles.button}
        aria-label="Следующий элемент"
        disabled={disabled}
        onClick={moveDown}
      >
        ↓
      </button>
    </div>
  );
};
