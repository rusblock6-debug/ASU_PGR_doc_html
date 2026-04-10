import styles from './MovementButton.module.css';

/** Неактивная плашка «ДВИЖЕНИЕ» под спидометром (макет). */
export const MovementButton = () => (
  <button
    type="button"
    className={styles.movement_button}
    disabled
    aria-label="Состояние движения"
  >
    <div className={styles.movement_text}>
      <span className={styles.movement_title}>ДВИЖЕНИЕ</span>
      <span className={styles.movement_sub}>—</span>
    </div>
    <svg
      viewBox="0 0 24 24"
      className={styles.movement_arrow}
      aria-hidden
    >
      <path d="M9 6l6 6-6 6" />
    </svg>
  </button>
);
