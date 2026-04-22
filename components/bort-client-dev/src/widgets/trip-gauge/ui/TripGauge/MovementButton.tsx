import ChevronRightIcon from '@/shared/assets/icons/ic-chevron-right.svg?react';

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
    <ChevronRightIcon
      className={styles.movement_arrow}
      aria-hidden
    />
  </button>
);
