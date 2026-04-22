import { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';

import { selectWifiConnected } from '@/shared/api/endpoints/vehicle-state';
import { useGetVehicleByIdQuery } from '@/shared/api/endpoints/vehicles';
import MapPinIcon from '@/shared/assets/icons/ic-map-pin.svg?react';
import VehicleLinkIcon from '@/shared/assets/icons/ic-vehicle-link.svg?react';
import WifiIcon from '@/shared/assets/icons/ic-wifi.svg?react';
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
  /** Метка текущей локации (отображается по центру шапки). */
  readonly locationLabel?: string;
  /** Дополнительная строка под локацией (напр. время перехода). */
  readonly locationSubLabel?: string;
  /** Усиленное отображение блока локации (используется на главном экране). */
  readonly highlightLocation?: boolean;
  /** Дополнительный CSS-класс корневого элемента. */
  readonly className?: string;
}

const formatClock = (d: Date) => d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', hour12: false });

const formatDate = (d: Date) => d.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'short' });

/**
 * Верхняя панель борта: техника, водитель, локация, время.
 */
export const KioskHeader = ({
  locationLabel = NO_DATA.LONG_DASH,
  locationSubLabel,
  highlightLocation = false,
  className,
}: KioskHeaderProps) => {
  const [now, setNow] = useState(() => new Date());
  const { user } = useAuth();
  const { data: vehicle, isLoading: isVehicleLoading } = useGetVehicleByIdQuery(VEHICLE_ID_NUM);
  const wifiConnected = useSelector(selectWifiConnected);

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
          <VehicleLinkIcon
            className={styles.left_glyph}
            aria-hidden
          />
          <div className={styles.left_text}>
            <div className={styles.vehicle}>{vehicleLabel}</div>
            <div className={styles.driver}>{driverName}</div>
          </div>
        </div>
      </div>
      <div className={styles.center}>
        <div className={styles.center_row}>
          {highlightLocation ? (
            <MapPinIcon
              className={styles.location_icon}
              aria-hidden
            />
          ) : null}
          <div className={styles.center_text}>
            <div className={cn(styles.location, highlightLocation && styles.location_highlight)}>{locationLabel}</div>
            {locationSubLabel ? (
              <div className={cn(styles.location_time, highlightLocation && styles.location_time_highlight)}>
                {locationSubLabel}
              </div>
            ) : null}
          </div>
        </div>
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
          <WifiIcon
            className={cn(styles.signal_icon, wifiConnected && styles.signal_icon_online)}
            aria-hidden
          />
        </div>
      </div>
    </header>
  );
};
