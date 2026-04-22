import { type ChangeEvent, type ReactNode, useState } from 'react';

import LoupeIcon from '@/shared/assets/icons/ic-loupe.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { ScrollArea } from '@/shared/ui/ScrollArea';
import { TextInput } from '@/shared/ui/TextInput';

import styles from './CategorizedList.module.css';

/** Представляет информацию о категории элемента. */
export interface CategoryInfo {
  /** Возвращает ключ категории для группировки. */
  readonly key: string;
  /** Возвращает отображаемое название категории. */
  readonly label: string;
}

/** Представляет свойства компонента категоризированного списка. */
interface CategorizedListProps<T> {
  /** Возвращает массив элементов. */
  readonly items: readonly T[];
  /** Возвращает признак доступности поиска. */
  readonly searchable?: boolean;
  /** Возвращает делегат, вызываемый при выборе элемента. */
  readonly onSelect?: (item: T) => void;
  /** Возвращает уникальный ключ элемента. */
  readonly getItemKey: (item: T) => string | number;
  /** Возвращает информацию о категории элемента. */
  readonly getCategory: (item: T) => CategoryInfo;
  /** Возвращает текст элемента для фильтрации по поиску. */
  readonly getSearchText: (item: T) => string;
  /** Возвращает содержимое элемента списка. */
  readonly renderItem: (item: T) => ReactNode;
  /** Возвращает высоту области прокрутки. */
  readonly scrollAreaHeight?: number;
  /** Возвращает сообщение при отсутствии данных. */
  readonly noDataMessage?: string;
}

/**
 * Представляет обобщённый компонент категоризированного списка с поиском.
 */
export function CategorizedList<T>(props: CategorizedListProps<T>) {
  const {
    items,
    onSelect,
    getItemKey,
    getCategory,
    getSearchText,
    renderItem,
    searchable = false,
    scrollAreaHeight = 336,
    noDataMessage = 'Нет данных',
  } = props;

  const [inputValue, setInputValue] = useState('');

  const onInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    setInputValue(event.target.value);
  };

  const onInputClear = () => {
    setInputValue('');
  };

  const normalizedQuery = inputValue.trim().toLowerCase();

  const filteredItems = items.filter((item) => getSearchText(item).trim().toLowerCase().includes(normalizedQuery));

  const canSelect = Boolean(onSelect);

  const categoryMap = new Map<string, { label: string; items: T[] }>();

  for (const item of filteredItems) {
    const { key, label } = getCategory(item);
    const existing = categoryMap.get(key);

    if (existing) {
      existing.items.push(item);
    } else {
      categoryMap.set(key, { label, items: [item] });
    }
  }

  return (
    <div>
      {searchable && (
        <TextInput
          size="xs"
          variant="outline"
          placeholder="Поиск"
          leftSection={<LoupeIcon className={styles.input_icon} />}
          clearable={inputValue.length > 0}
          className={styles.input}
          styles={{ input: { ['--input-padding']: '30px', ['--input-height']: '26px' } }}
          value={inputValue}
          onChange={onInputChange}
          onClear={onInputClear}
        />
      )}
      <ScrollArea
        h={scrollAreaHeight}
        scrollbars="y"
        scrollbarSize={4}
      >
        <div className={styles.container}>
          {filteredItems.length > 0 ? (
            Array.from(categoryMap.entries()).map(([key, category]) => (
              <div
                key={key}
                className={styles.category_container}
              >
                <p className={styles.category_title}>{category.label}</p>
                {category.items.map((item) => (
                  <div
                    key={getItemKey(item)}
                    className={cn(styles.item, { [styles.selectable]: canSelect })}
                    onClick={() => onSelect?.(item)}
                  >
                    {renderItem(item)}
                  </div>
                ))}
              </div>
            ))
          ) : (
            <div className={styles.no_data}>{noDataMessage}</div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
