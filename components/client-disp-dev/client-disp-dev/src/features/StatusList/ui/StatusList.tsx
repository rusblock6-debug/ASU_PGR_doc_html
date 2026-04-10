import { type ChangeEvent, useMemo, useState } from 'react';

import type { Status } from '@/shared/api/endpoints/statuses';
import { cn } from '@/shared/lib/classnames-utils';
import { ScrollArea } from '@/shared/ui/ScrollArea';
import { StatusIcon } from '@/shared/ui/StatusIcon';
import { TextInput } from '@/shared/ui/TextInput';

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
export function StatusList(props: StatusesListProps) {
  const { statuses, searchable = false, onSelect } = props;

  const [inputValue, setInputValue] = useState('');

  const onInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    setInputValue(event.target.value);
  };

  const onInputClear = () => {
    setInputValue('');
  };

  const filteredStatuses = useMemo(
    () =>
      statuses.filter((status) => status.display_name.trim().toLowerCase().includes(inputValue.trim().toLowerCase())),
    [inputValue, statuses],
  );

  const canSelected = Boolean(onSelect);

  const groupedByAnalyticCategory = useMemo(() => {
    return filteredStatuses.reduce<Record<string, Status[]>>((acc, status) => {
      const category = status.analytic_category;
      if (!acc[category]) {
        acc[category] = [];
      }
      acc[category].push(status);
      return acc;
    }, {});
  }, [filteredStatuses]);

  return (
    <div>
      {searchable && (
        <TextInput
          placeholder="Поиск"
          variant="outline"
          clearable
          className={styles.input}
          value={inputValue}
          onChange={onInputChange}
          onClear={onInputClear}
        />
      )}
      <ScrollArea h={336}>
        <div className={styles.statuses_container}>
          {filteredStatuses.length > 0 ? (
            Object.keys(groupedByAnalyticCategory).map((key) => (
              <div
                key={key}
                className={styles.statuses_list_container}
              >
                <p className={styles.statuses_list_title}>
                  {groupedByAnalyticCategory[key].at(0)?.analytic_category_display_name}
                </p>
                {groupedByAnalyticCategory[key].map((status) => (
                  <div
                    key={status.id}
                    className={cn(styles.status_item, { [styles.selectable]: canSelected })}
                    onClick={() => {
                      onSelect?.(status);
                    }}
                  >
                    <StatusIcon color={status.color} />
                    <p className={cn(styles.status_name, { [styles.selectable]: canSelected })}>
                      {status.display_name}
                    </p>
                  </div>
                ))}
              </div>
            ))
          ) : (
            <div className={styles.no_data}>Нет данных</div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
