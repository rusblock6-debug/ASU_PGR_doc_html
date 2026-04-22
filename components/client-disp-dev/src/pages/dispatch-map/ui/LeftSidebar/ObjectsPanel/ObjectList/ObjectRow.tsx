import type { ReactNode } from 'react';

import ArrowRightWithTailIcon from '@/shared/assets/icons/ic-arrow-right-with-tail.svg?react';
import PencilIcon from '@/shared/assets/icons/ic-pencil.svg?react';
import TargetIcon from '@/shared/assets/icons/ic-target-light.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { hasValueNotEmpty } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { Checkbox } from '@/shared/ui/Checkbox';
import { Tooltip } from '@/shared/ui/Tooltip';

import { useExitFormEdit } from '../../../../lib/hooks/useExitFormEdit';
import { GroupVisibility } from '../../../../model/lib/compute-group-visibility';
import {
  selectSelectedVehicleHistoryIds,
  selectFormTarget,
  selectIsVisibleHistoryPlayer,
  selectMapMode,
} from '../../../../model/selectors';
import { mapActions } from '../../../../model/slice';
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
  const dispatch = useAppDispatch();
  const mapMode = useAppSelector(selectMapMode);
  const isVisibleHistoryPlayer = useAppSelector(selectIsVisibleHistoryPlayer);
  const formTarget = useAppSelector(selectFormTarget);
  const exitFormEdit = useExitFormEdit();
  const selectedVehicleHistoryIds = useAppSelector(selectSelectedVehicleHistoryIds);

  const handleChangeObject = async () => {
    if (formTarget?.id === item.id) return;

    const canProceed = await exitFormEdit('Вы действительно хотите выбрать другой объект?');
    if (!canProceed) return;

    onEdit?.(item.id);
  };

  const checked = selectedVehicleHistoryIds.includes(item.id);

  const handleShowHistory = () => {
    dispatch(mapActions.toggleVehicleHistoryId(item.id));
  };

  const isHistoryMode = mapMode === Mode.HISTORY;

  return (
    <div className={styles.row}>
      {isHistoryMode && !isVisibleHistoryPlayer && (
        <Checkbox
          size="xs"
          className={styles.checkbox}
          checked={checked}
          onChange={handleShowHistory}
        />
      )}

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

        {hasValueNotEmpty(item.horizon) && !isHistoryMode && (
          <IconButton
            disabled={hidden}
            title="Центрировать на карте"
            onClick={() => onLocate?.(item.id)}
          >
            <TargetIcon />
          </IconButton>
        )}

        {!isHistoryMode && (
          <VisibilityButton
            visibility={hidden ? GroupVisibility.HIDDEN : GroupVisibility.VISIBLE}
            onToggle={() => onToggleVisibility?.(item.id)}
          />
        )}

        {isHistoryMode && !isVisibleHistoryPlayer && (
          <IconButton
            title="История изменений"
            onClick={() => {
              console.log('клик по стрелочке в ряду "История изменений"');
            }}
          >
            <ArrowRightWithTailIcon />
          </IconButton>
        )}
      </span>
    </div>
  );
}
