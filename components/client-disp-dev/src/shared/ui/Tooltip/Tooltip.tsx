import type { TooltipProps as MantineTooltipProps } from '@mantine/core';
import { Tooltip as MantineTooltip } from '@mantine/core';
import type { ReactNode } from 'react';

import { Z_INDEX } from '@/shared/lib/constants';

import styles from './Tooltip.module.css';

/**
 * Представляет свойства для компонента тултипа.
 * https://mantine.dev/core/tooltip/
 */
export interface TooltipProps extends Omit<MantineTooltipProps, 'children'> {
  /** Содержимое тултипа */
  readonly label: ReactNode;
  /** Элемент, при наведении на который показывается тултип */
  readonly children: ReactNode;
  /** Задержка перед открытием в миллисекундах */
  readonly openDelay?: number;
  /** Позиция тултипа относительно целевого элемента */
  readonly position?: 'top' | 'bottom' | 'left' | 'right';
  /** Показывать стрелку */
  readonly withArrow?: boolean;
}

/**
 * Адаптер компонента Tooltip из Mantine с предустановленными значениями по умолчанию.
 */
export function Tooltip({
  label,
  children,
  openDelay = 300,
  multiline = true,
  position = 'top',
  withArrow = false,
  ...props
}: TooltipProps) {
  return (
    <MantineTooltip
      label={label}
      openDelay={openDelay}
      position={position}
      withArrow={withArrow}
      multiline={multiline}
      offset={4}
      transitionProps={{ transition: 'pop', duration: 200 }}
      classNames={{
        tooltip: styles.tooltip,
      }}
      zIndex={Z_INDEX.TOOLTIP}
      {...props}
    >
      {children}
    </MantineTooltip>
  );
}
