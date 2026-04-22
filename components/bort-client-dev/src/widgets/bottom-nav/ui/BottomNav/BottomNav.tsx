import { useNavigate } from 'react-router-dom';

import BurgerIcon from '@/shared/assets/icons/ic-burger.svg?react';
import HistoryIcon from '@/shared/assets/icons/ic-history.svg?react';
import TaskIcon from '@/shared/assets/icons/ic-task-fill.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { getRouteMainMenu, getRouteVehicleStatus, getRouteWorkOrders } from '@/shared/routes/router';

import styles from './BottomNav.module.css';

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
        onClick={() => navigate(getRouteVehicleStatus())}
        aria-label="Открыть управление статусом"
      >
        <HistoryIcon
          className={styles.icon}
          aria-hidden
        />
      </button>
      <button
        className={styles.button}
        type="button"
        onClick={() => navigate(getRouteWorkOrders())}
        aria-label="Открыть наряд-задания"
      >
        <TaskIcon
          className={cn(styles.icon, styles.icon_check)}
          aria-hidden
        />
      </button>
      <button
        className={styles.button}
        type="button"
        onClick={() => navigate(getRouteMainMenu())}
        aria-label="Открыть меню"
      >
        <BurgerIcon
          className={cn(styles.icon, styles.icon_menu)}
          aria-hidden
        />
      </button>
    </nav>
  );
};
