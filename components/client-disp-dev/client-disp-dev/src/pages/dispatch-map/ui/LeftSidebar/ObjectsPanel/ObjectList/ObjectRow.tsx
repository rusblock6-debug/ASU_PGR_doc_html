import type { ReactNode } from 'react';

import PencilIcon from '@/shared/assets/icons/ic-pencil.svg?react';
import TargetIcon from '@/shared/assets/icons/ic-target-light.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { useConfirm } from '@/shared/lib/confirm';
import { hasValueNotEmpty } from '@/shared/lib/has-value';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { Tooltip } from '@/shared/ui/Tooltip';

import { GroupVisibility } from '../../../../model/lib/compute-group-visibility';
import { selectFormTarget, selectHasUnsavedChanges, selectMapMode } from '../../../../model/selectors';
import { Mode } from '../../../../model/types';
import { IconButton, VisibilityButton } from '../../IconButton';

import styles from './ObjectRow.module.css';

/**
 * Представляет данные объекта в списке {@link ObjectList}.
 */
export interface ObjectItem {
  /** Уникальный идентификатор. */
  readonly id: number;
  /** Иконка типа объекта. */
  readonly icon?: ReactNode;
  /** Наименование объекта. */
  readonly name: string;
  /** Остаток (опционально). */
  readonly stock?: string;
  /** Горизонт. */
  readonly horizon: string;
}

/**
 * Представляет свойства компонента {@link ObjectRow}.
 */
interface ObjectRowProps {
  /** Данные объекта. */
  readonly item: ObjectItem;
  /** Показывать ли колонку «Остаток». */
  readonly hasStock?: boolean;
  /** Показывать ли колонку «Горизонт». */
  readonly hasHorizon?: boolean;
  /** Скрыт ли объект на карте. */
  readonly hidden?: boolean;
  /** Колбэк наведения камеры на объект. */
  readonly onLocate?: (id: number) => void;
  /** Колбэк переключения видимости объекта. */
  readonly onToggleVisibility?: (id: number) => void;
  /** Колбэк изменения объекта. */
  readonly onEdit?: (id: number) => void;
}

/**
 * Строка объекта в списке {@link ObjectList}.
 */
export function ObjectRow({
  item,
  hasStock = true,
  hasHorizon = true,
  hidden = false,
  onLocate,
  onToggleVisibility,
  onEdit,
}: ObjectRowProps) {
  const mapMode = useAppSelector(selectMapMode);
  const hasUnsavedChanges = useAppSelector(selectHasUnsavedChanges);
  const formTarget = useAppSelector(selectFormTarget);
  const confirm = useConfirm();

  const handleChangeObject = async () => {
    if (hasUnsavedChanges && formTarget?.id !== item.id) {
      const isConfirmed = await confirm({
        title: 'Вы действительно хотите выбрать другой объект?',
        message: `Текущие изменения будут утеряны.`,
        confirmText: 'Продолжить',
        cancelText: 'Отмена',
        size: 'md',
      });

      if (isConfirmed) {
        onEdit?.(item.id);
      }

      return;
    }

    if (formTarget?.id === item.id) return;

    onEdit?.(item.id);
  };

  return (
    <div className={styles.row}>
      <span className={styles.icon}>{item.icon}</span>

      <span className={cn(styles.name, 'truncate')}>
        <Tooltip label={item.name}>
          <span>{item.name}</span>
        </Tooltip>
      </span>

      {hasStock && <span className={styles.stock}>{item.stock}</span>}
      {hasHorizon && <span className={styles.horizon}>{item.horizon}</span>}

      <span className={styles.actions}>
        {mapMode === Mode.EDIT && (
          <IconButton
            title="Изменить объект"
            onClick={handleChangeObject}
          >
            <PencilIcon />
          </IconButton>
        )}

        {hasValueNotEmpty(item.horizon) && (
          <IconButton
            title="Центрировать на карте"
            onClick={() => onLocate?.(item.id)}
          >
            <TargetIcon />
          </IconButton>
        )}

        <VisibilityButton
          visibility={hidden ? GroupVisibility.HIDDEN : GroupVisibility.VISIBLE}
          onToggle={() => onToggleVisibility?.(item.id)}
        />
      </span>
    </div>
  );
}
