import type { PropsWithChildren, ReactNode } from 'react';

import { formatNumber } from '@/shared/lib/format-number';
import { hasValue } from '@/shared/lib/has-value';
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
  /** Элемент, размещенный в `leftSection` компонента `Collapsible`. */
  readonly leftSectionComponent?: ReactNode;
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
    onToggleVisibility,
    className,
    leftSectionComponent,
    children,
  } = props;

  const [isExpanded, toggle] = useTreeNodeExpanded(groupKey);

  return (
    <Collapsible
      className={className}
      label={label}
      opened={isExpanded}
      disabled={disabled}
      onToggle={toggle}
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
