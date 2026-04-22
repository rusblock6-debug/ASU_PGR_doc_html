import type { Status } from '@/shared/api/endpoints/statuses';
import { CategorizedList } from '@/shared/ui/CategorizedList';
import { StatusIcon } from '@/shared/ui/StatusIcon';

import styles from './StatusList.module.css';

/** Представляет свойства компонента списка статусов. */
interface StatusesListProps {
  /** Возвращает список статусов. */
  readonly statuses: readonly Status[];
  /** Возвращает признак доступности поиска. */
  readonly searchable?: boolean;
  /** Возвращает делегат, вызываемый при выборе статуса. */
  readonly onSelect?: (status: Status) => void;
}

/**
 * Представляет компонент списка статусов.
 */
export function StatusList({ statuses, searchable = false, onSelect }: StatusesListProps) {
  return (
    <CategorizedList
      items={statuses}
      searchable={searchable}
      onSelect={onSelect}
      getItemKey={(status) => status.id}
      getCategory={(status) => ({
        key: status.analytic_category,
        label: status.analytic_category_display_name,
      })}
      getSearchText={(status) => status.display_name}
      renderItem={(status) => (
        <>
          <StatusIcon color={status.color} />
          <p className={styles.status_name}>{status.display_name}</p>
        </>
      )}
    />
  );
}
