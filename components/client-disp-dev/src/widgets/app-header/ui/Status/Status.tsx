import PlanetIcon from '@/shared/assets/icons/ic-planet.svg?react';
import { cn } from '@/shared/lib/classnames-utils';

import { useCurrentTime } from '../../lib/useCurrentTime';
import { useNetworkStatus } from '../../lib/useNetworkStatus';

import styles from './Status.module.css';

export function Status() {
  const currentTime = useCurrentTime();
  const hasConnection = useNetworkStatus();

  return (
    <div className={styles.connection_info}>
      <p className={cn(styles.connection_status, { [styles.connection_status_bad]: !hasConnection })}>
        <PlanetIcon
          width={16}
          height={16}
        />{' '}
        {hasConnection ? 'подключение успешно' : 'подключение отсутствует'}
      </p>
      <p className={styles.connection_time}>{currentTime}</p>
    </div>
  );
}
