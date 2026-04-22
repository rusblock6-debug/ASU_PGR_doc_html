import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';

import styles from './ConfirmButton.module.css';

/**
 * Пропсы кнопки подтверждения.
 */
interface ConfirmButtonProps {
  readonly disabled?: boolean;
}

/**
 * Подтверждение текущего действия (открыть выбранный маршрут и т. п.).
 */
export const ConfirmButton = ({ disabled: disabledProp }: ConfirmButtonProps) => {
  const { confirm, itemIds } = useKioskNavigation();
  const disabled = disabledProp ?? itemIds.length === 0;

  return (
    <button
      type="button"
      className={styles.root}
      aria-label="Подтвердить"
      disabled={disabled}
      onClick={confirm}
    >
      ✓
    </button>
  );
};
