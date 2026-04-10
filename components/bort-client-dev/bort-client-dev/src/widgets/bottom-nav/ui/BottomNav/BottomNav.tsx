import { useNavigate } from 'react-router-dom';

import { cn } from '@/shared/lib/classnames-utils';
import { getRouteMainMenu, getRouteWorkOrders } from '@/shared/routes/router';

import styles from './BottomNav.module.css';

/** Иконка «Настройки». */
const GearIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden
    className={cn(styles.icon, styles.icon_gear)}
  >
    <path d="M9.5 3.8h5l.8 2.3 2.4 1.4 2.2-.9 2.5 4.3-1.8 1.5v2.8l1.8 1.5-2.5 4.3-2.2-.9-2.4 1.4-.8 2.3h-5l-.8-2.3-2.4-1.4-2.2.9-2.5-4.3 1.8-1.5v-2.8L1 10.9l2.5-4.3 2.2.9 2.4-1.4z" />
    <circle
      cx="12"
      cy="14"
      r="2.5"
    />
  </svg>
);

/** Иконка «История». */
const HistoryIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden
    className={styles.icon}
  >
    <path d="M4 12a8 8 0 1 0 2.3-5.7M4 4v4h4" />
    <path d="M12 8v4l2.7 2.7" />
  </svg>
);

/** Иконка «Наряд-задания». */
const CheckTaskIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden
    className={cn(styles.icon, styles.icon_check)}
  >
    <path d="M9 4.5h6M9 3h6a1.5 1.5 0 0 1 1.5 1.5v1H7.5v-1A1.5 1.5 0 0 1 9 3Z" />
    <path d="M7.5 5.5H6A1.5 1.5 0 0 0 4.5 7v12A1.5 1.5 0 0 0 6 20.5h12a1.5 1.5 0 0 0 1.5-1.5V7A1.5 1.5 0 0 0 18 5.5h-1.5" />
    <path d="M8 12.5l2 2 4-4" />
  </svg>
);

/** Иконка «Меню». */
const MenuIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden
    className={cn(styles.icon, styles.icon_menu)}
  >
    <path d="M5 8h14M5 12h14M5 16h14" />
  </svg>
);

/**
 * Нижняя навигационная панель kiosk-интерфейса.
 */
export const BottomNav = () => {
  const navigate = useNavigate();

  return (
    <nav
      className={styles.root}
      aria-label="Нижняя навигация"
    >
      <button
        className={styles.button}
        type="button"
        disabled
        aria-label="Настройки (пока недоступно)"
      >
        <GearIcon />
      </button>
      <button
        className={styles.button}
        type="button"
        disabled
        aria-label="История (пока недоступно)"
      >
        <HistoryIcon />
      </button>
      <button
        className={styles.button}
        type="button"
        onClick={() => navigate(getRouteWorkOrders())}
        aria-label="Открыть наряд-задания"
      >
        <CheckTaskIcon />
      </button>
      <button
        className={styles.button}
        type="button"
        onClick={() => navigate(getRouteMainMenu())}
        aria-label="Открыть меню"
      >
        <MenuIcon />
      </button>
    </nav>
  );
};
