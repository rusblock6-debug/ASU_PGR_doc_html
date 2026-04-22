import ArrowsUpDownIcon from '@/shared/assets/icons/ic-arrows-up-down.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import type { SortState } from '@/shared/lib/sort-by-field';

import { IconButton } from '../IconButton';

import styles from './SortIconButton.module.css';

/** Свойства компонента {@link SortIconButton}. */
interface SortIconButtonProps<TField extends string> {
  /** Поле сортировки. */
  readonly field: TField;
  /** Текущее состояние сортировки. */
  readonly sortState: SortState<TField>;
  /** Колбэк смены сортировки по полю. */
  readonly onSortChange: (field: TField) => void;
}

/**
 * Кнопка сортировки с иконкой стрелок.
 * При активной сортировке по этой колонке подсвечивает активную стрелку.
 */
export function SortIconButton<TField extends string>({ field, sortState, onSortChange }: SortIconButtonProps<TField>) {
  const isActive = sortState.field === field;
  const orderLabel = sortState.order === 'asc' ? 'по возрастанию' : 'по убыванию';
  const title = isActive ? `Сортировка: ${orderLabel}` : 'Отсортировать';

  return (
    <IconButton
      title={title}
      onClick={() => onSortChange(field)}
      className={cn(
        styles.button,
        isActive && sortState.order === 'asc' && styles.button_asc,
        isActive && sortState.order === 'desc' && styles.button_desc,
      )}
    >
      <ArrowsUpDownIcon />
    </IconButton>
  );
}
