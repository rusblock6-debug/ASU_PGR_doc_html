import { useEffect, useState } from 'react';

import { useGetVehicleByIdQuery } from '@/shared/api';
import { VEHICLE_ID_NUM } from '@/shared/config/env';
import { useAuth } from '@/shared/lib/auth';
import { cn } from '@/shared/lib/classnames-utils';
import { NO_DATA } from '@/shared/lib/constants';

import styles from './KioskHeader.module.css';

const VEHICLE_LABEL_FALLBACK = import.meta.env.VITE_KIOSK_VEHICLE_LABEL || 'Техника';
const DRIVER_NAME_FALLBACK = import.meta.env.VITE_KIOSK_DRIVER_NAME || NO_DATA.LONG_DASH;

/**
 * Пропсы шапки kiosk-интерфейса.
 */
interface KioskHeaderProps {
  readonly locationLabel?: string;
  readonly locationSubLabel?: string;
  readonly className?: string;
}

const formatClock = (d: Date) => d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', hour12: false });

const formatDate = (d: Date) => d.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'short' });

/** Декоративная иконка слева в шапке (макет). */
const VehicleLinkIcon = () => (
  <svg
    viewBox="0 0 24 24"
    className={styles.left_glyph}
    aria-hidden
  >
    <circle
      cx="6"
      cy="12"
      r="2.25"
    />
    <circle
      cx="18"
      cy="12"
      r="2.25"
    />
    <path d="M8.25 12h7.5" />
  </svg>
);

/** Иконка Wi‑Fi в шапке. */
const WifiIcon = () => (
  <svg
    viewBox="0 0 24 24"
    className={styles.signal_icon}
    aria-hidden
  >
    <path d="M5 9.5c3.5-3.5 10.5-3.5 14 0M8 12.5c2.2-2.2 5.8-2.2 8 0M11 15.5c.8-.8 2.2-.8 3 0" />
    <circle
      cx="12.5"
      cy="18"
      r="1.2"
    />
  </svg>
);

/** Иконка уровня сотовой связи в шапке. */
const CellularIcon = () => (
  <svg
    viewBox="0 0 24 24"
    className={styles.signal_icon}
    aria-hidden
  >
    <path d="M5 18V14M9 18v-5M13 18V9M17 18V6" />
  </svg>
);

/**
 * Верхняя панель борта: техника, водитель, локация, время.
 */
export const KioskHeader = ({ locationLabel = NO_DATA.LONG_DASH, locationSubLabel, className }: KioskHeaderProps) => {
  const [now, setNow] = useState(() => new Date());
  const { user } = useAuth();
  const { data: vehicle, isLoading: isVehicleLoading } = useGetVehicleByIdQuery(VEHICLE_ID_NUM);

  const trimmedVehicleName = typeof vehicle?.name === 'string' ? vehicle.name.trim() : '';
  const vehicleLabel = isVehicleLoading ? NO_DATA.ELLIPSIS : trimmedVehicleName || VEHICLE_LABEL_FALLBACK;

  const driverName = user?.displayName?.trim() || DRIVER_NAME_FALLBACK;

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <header className={cn(styles.root, className)}>
      <div className={styles.left}>
        <div className={styles.left_row}>
          <VehicleLinkIcon />
          <div className={styles.left_text}>
            <div className={styles.vehicle}>{vehicleLabel}</div>
            <div className={styles.driver}>{driverName}</div>
          </div>
        </div>
      </div>
      <div className={styles.center}>
        <div className={styles.location}>{locationLabel}</div>
        {locationSubLabel ? <div className={styles.location_time}>{locationSubLabel}</div> : null}
      </div>
      <div className={styles.right}>
        <div className={styles.right_time_block}>
          <div className={styles.clock}>{formatClock(now)}</div>
          <div className={styles.date}>{formatDate(now)}</div>
        </div>
        <div
          className={styles.signal_row}
          aria-hidden
        >
          <WifiIcon />
          <CellularIcon />
        </div>
      </div>
    </header>
  );
};
