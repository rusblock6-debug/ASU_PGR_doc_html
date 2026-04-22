import { useEffect } from 'react';
import { Link } from 'react-router-dom';

import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';
import { getRouteWorkOrders } from '@/shared/routes/router';

import styles from './SessionEndedPage.module.css';

/**
 * Заглушка после завершения смены (до внедрения авторизации).
 */
export const SessionEndedPage = () => {
  const { setItemIds, setOnConfirm } = useKioskNavigation();

  useEffect(() => {
    setItemIds([]);
    setOnConfirm(null);
  }, [setItemIds, setOnConfirm]);

  return (
    <div className={styles.root}>
      <h1 className={styles.title}>Смена завершена</h1>
      <p className={styles.text}>Вы вышли из смены. Войдите снова, когда будет готова авторизация.</p>
      <Link
        className={styles.link}
        to={getRouteWorkOrders()}
      >
        К наряд-заданиям
      </Link>
    </div>
  );
};
