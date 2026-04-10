import 'dayjs/locale/ru';

import type { ReactNode } from 'react';

import PlusIcon from '@/shared/assets/icons/ic-plus.svg?react';
import TrashIcon from '@/shared/assets/icons/ic-trash.svg?react';
import { useConfirm } from '@/shared/lib/confirm';
import { ruPlural } from '@/shared/lib/plural';
import { Button } from '@/shared/ui/Button';

import { useTableContext } from '../../model/TableContext';

import styles from './ControlPanel.module.css';

interface ControlPanelProps {
  /**
   * Возвращает элемент, расположенный по центру.
   */
  readonly centerContent?: ReactNode;
  /**
   * Возвращает элемент, расположенный после элемента статистики.
   */
  readonly afterStatisticsContent?: ReactNode;
  readonly onDateChange?: (date: Date | null) => void;
}

export function ControlPanel<TData extends Record<string, unknown>>({
  centerContent,
  afterStatisticsContent,
}: ControlPanelProps) {
  const context = useTableContext<TData>();
  const confirm = useConfirm();

  const handleAddClick = context?.openAddDrawer;

  const selectedRows = context?.selectedRows ?? [];
  const hasSelectedRows = selectedRows.length > 0;

  const handleDelete = async () => {
    if (!hasSelectedRows || !context) return;

    const count = selectedRows.length;
    const confirmed = await confirm({
      title: `Вы действительно хотите удалить ${count}\u00A0${ruPlural(count, 'объект', 'объекта', 'объектов')} из справочника?`,
      confirmText: 'Удалить',
    });

    if (!confirmed) return;

    if (context.onDelete) {
      const ids = selectedRows.map(context.getRowId);
      await context.onDelete(ids);
      context.setSelectedRows([]);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.actions}>
        <Button
          variant="primary"
          size="extra-small"
          onClick={handleAddClick}
        >
          <PlusIcon /> Добавить
        </Button>
        {hasSelectedRows && (
          <Button
            variant="clear"
            size="extra-small"
            onClick={handleDelete}
            className={styles.remove_button}
          >
            <TrashIcon /> Удалить
          </Button>
        )}
        {centerContent}
      </div>

      <div className={styles.statistics}>
        {hasSelectedRows && (
          <p>
            выделено: {selectedRows.length} {ruPlural(selectedRows.length, 'объект', 'объекта', 'объектов')}
          </p>
        )}
        {!!context?.total && (
          <p>
            всего: {context?.total} {ruPlural(context?.total, 'объект', 'объекта', 'объектов')}
          </p>
        )}
      </div>
      {afterStatisticsContent}
    </div>
  );
}
