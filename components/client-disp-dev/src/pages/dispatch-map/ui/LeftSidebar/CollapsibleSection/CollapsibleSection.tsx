import { type ChangeEvent, type PropsWithChildren, type ReactNode } from 'react';

import { cn } from '@/shared/lib/classnames-utils';
import { formatNumber } from '@/shared/lib/format-number';
import { hasValue } from '@/shared/lib/has-value';
import { Checkbox } from '@/shared/ui/Checkbox';
import { Collapsible } from '@/shared/ui/Collapsible';

import { useTreeNodeExpanded } from '../../../lib/hooks/useTreeNodeExpanded';
import type { GroupVisibilityValue } from '../../../model/lib/compute-group-visibility';
import type { TreeNodeValue } from '../../../model/types';
import { VisibilityButton } from '../IconButton';

import styles from './CollapsibleSection.module.css';

/**
 * Представляет свойства компонента {@link CollapsibleSection}.
 */
interface CollapsibleSectionProps {
  /** Заголовок группы. */
  readonly label: string;
  /** Уникальный ключ группы (для управления раскрытием). */
  readonly groupKey: TreeNodeValue;
  /** Количество объектов в секции. */
  readonly count?: number;
  /** Видимость группы. */
  readonly visibility?: GroupVisibilityValue;
  /** Колбэк переключения видимости группы. */
  readonly onToggleVisibility?: () => void;
  /** Дополнительный className для корневого элемента. */
  readonly className?: string;
  /** Блокирует раскрытие, скрывает стрелочку (например, когда нет данных) и кнопку показать/скрыть. */
  readonly disabled?: boolean;
  /** Принудительно раскрывает секцию (например, при поиске), не затрагивая Redux-стейт. */
  readonly forceExpanded?: boolean;
  /** Элемент, размещенный в `leftSection` компонента `Collapsible`. */
  readonly leftSectionComponent?: ReactNode;
  /** Состояние выбора группы. */
  readonly checked?: boolean;
  /** Колбэк переключения выбора группы. */
  readonly onCheckChange?: (checked: boolean) => void;
}

/**
 * Сворачиваемая группа объектов в дереве сайдбара.
 */
export function CollapsibleSection(props: PropsWithChildren<CollapsibleSectionProps>) {
  const {
    label,
    groupKey,
    count,
    visibility,
    disabled = false,
    forceExpanded = false,
    onToggleVisibility,
    className,
    leftSectionComponent,
    checked,
    onCheckChange,
    children,
  } = props;

  const [isExpanded, toggle] = useTreeNodeExpanded(groupKey);

  const onCheckboxChange = (event: ChangeEvent<HTMLInputElement>) => {
    return onCheckChange?.(event.target.checked);
  };

  return (
    <Collapsible
      className={className}
      label={label}
      opened={forceExpanded || isExpanded}
      disabled={disabled}
      locked={forceExpanded}
      transitionDuration={forceExpanded ? 0 : undefined}
      onToggle={toggle}
      beforeHeaderContent={
        onCheckChange ? (
          <Checkbox
            size="xs"
            className={cn(styles.checkbox, { [styles.visible]: hasValue(count) && count > 0 })}
            onChange={onCheckboxChange}
            checked={checked}
          />
        ) : undefined
      }
      leftSection={
        <>
          {hasValue(count) ? <span className={styles.count}>{formatNumber(count)}</span> : undefined}
          {leftSectionComponent}
        </>
      }
      rightSection={
        onToggleVisibility && visibility && !disabled ? (
          <VisibilityButton
            visibility={visibility}
            onToggle={onToggleVisibility}
          />
        ) : undefined
      }
    >
      {children}
    </Collapsible>
  );
}
