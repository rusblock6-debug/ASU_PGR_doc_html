import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { cn } from '@/shared/lib/classnames-utils';
import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';
import { getRouteMain, getRouteSettings, getRouteStats, getRouteVehicleStatus } from '@/shared/routes/router';

import styles from './MainMenuPage.module.css';

/** Элемент сетки главного меню (маршрут, подпись, опционально disabled). */
interface MenuItemDef {
  readonly id: string;
  readonly label: string;
  readonly route: () => string;
  readonly disabled?: boolean;
  readonly className?: string;
}

const MENU_ITEMS: readonly MenuItemDef[] = [
  { id: 'current-task', label: 'ТЕКУЩЕЕ ЗАДАНИЕ', route: getRouteMain },
  { id: 'events-top', label: 'ЖУРНАЛ СОБЫТИЙ', route: getRouteVehicleStatus },
  { id: 'settings', label: 'НАСТРОЙКИ', route: getRouteSettings },
  { id: 'stats', label: 'СТАТИСТИКА', route: getRouteStats },
];

const MENU_ITEM_IDS = MENU_ITEMS.map((item) => item.id);

/** Сетка пунктов главного меню (текущее задание, заглушки). */
export const MainMenuPage = () => {
  const navigate = useNavigate();
  const { selectedId, setItemIds, setOnConfirm } = useKioskNavigation();

  useEffect(() => {
    setItemIds(MENU_ITEM_IDS);
  }, [setItemIds]);

  useEffect(() => {
    setOnConfirm(async () => {
      if (!selectedId) {
        return;
      }
      const selected = MENU_ITEMS.find((item) => item.id === selectedId);
      if (!selected || selected.disabled) {
        return;
      }
      await navigate(selected.route());
    });
    return () => {
      setOnConfirm(null);
    };
  }, [selectedId, setOnConfirm, navigate]);

  return (
    <div className={styles.page}>
      <div className={styles.grid}>
        {MENU_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={cn(styles.item, selectedId === item.id && styles.item_selected, item.className)}
            disabled={item.disabled}
            onClick={() => navigate(item.route())}
            aria-label={item.label}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
};
