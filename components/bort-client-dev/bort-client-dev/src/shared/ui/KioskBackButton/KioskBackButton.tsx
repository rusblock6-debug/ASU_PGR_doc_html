import styles from './KioskBackButton.module.css';

/** Пропсы кнопки возврата на kiosk-экранах. */
interface KioskBackButtonProps {
  readonly onClick: () => void;
}

/**
 * Кнопка «Назад» для kiosk-экранов.
 */
export const KioskBackButton = ({ onClick }: KioskBackButtonProps) => (
  <button
    type="button"
    className={styles.root}
    aria-label="Назад"
    onClick={onClick}
  >
    ←
  </button>
);
