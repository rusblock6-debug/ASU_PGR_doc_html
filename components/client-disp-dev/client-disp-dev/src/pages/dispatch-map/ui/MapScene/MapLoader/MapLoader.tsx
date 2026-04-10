import { cn } from '@/shared/lib/classnames-utils';

import styles from './MapLoader.module.css';

export function MapLoader() {
  return (
    <div className={styles.loader}>
      <div className={cn(styles.loader_icon, 'loader')}></div>
      <div className={styles.loader_text}>Загрузка данных</div>
    </div>
  );
}
