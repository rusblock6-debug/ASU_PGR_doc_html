import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { cn } from '@/shared/lib/classnames-utils';
import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';
import { getRouteMain } from '@/shared/routes/router';

import styles from './MainMenuPage.module.css';

/** Пункт сетки главного меню kiosk. */
interface MenuItem {
  readonly id: string;
  readonly label: string;
  readonly disabled?: boolean;
  readonly onClick?: () => void;
  readonly className?: string;
}

/** Сетка пунктов главного меню (текущее задание, заглушки). */
export const MainMenuPage = () => {
  const navigate = useNavigate();
  const { setItemIds, setOnConfirm } = useKioskNavigation();

  useEffect(() => {
    setItemIds([]);
    setOnConfirm(null);
  }, [setItemIds, setOnConfirm]);

  const menuItems: readonly MenuItem[] = [
    {
      id: 'current-task',
      label: 'ТЕКУЩЕЕ ЗАДАНИЕ',
      onClick: () => navigate(getRouteMain()),
    },
    {
      id: 'events-top',
      label: 'ЖУРНАЛ СОБЫТИЙ',
      disabled: true,
    },
    {
      id: 'settings',
      label: 'НАСТРОЙКИ',
      disabled: true,
    },
    {
      id: 'stats',
      label: 'СТАТИСТИКА',
      disabled: true,
    },
  ];

  return (
    <div className={styles.page}>
      <div className={styles.grid}>
        {menuItems.map((item) => (
          <button
            key={item.id}
            type="button"
            className={cn(styles.item, item.className)}
            disabled={item.disabled}
            onClick={item.onClick}
            aria-label={item.label}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
};
