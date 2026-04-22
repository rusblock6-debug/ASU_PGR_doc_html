import { useCallback } from 'react';
import {
  Panel,
  Group,
  Separator,
  type SeparatorProps,
  type PanelProps,
  type GroupProps,
  type PanelSize,
} from 'react-resizable-panels';

import DragHandleDotsIcon from '@/shared/assets/icons/ic-drag-handle-dots.svg?react';
import { cn } from '@/shared/lib/classnames-utils';

import styles from './Resizable.module.css';
import { ResizeProvider, useResizeContext } from './ResizeContext';

/**
 * Представляет компонент группы элементов с изменяемыми размерами.
 */
export function ResizablePanelGroup({ className, ...props }: GroupProps) {
  return (
    <ResizeProvider>
      <Group
        data-slot="resizable-panel-group"
        className={cn(styles.resizable_panel_group, className)}
        {...props}
      />
    </ResizeProvider>
  );
}

/**
 * Представляет компонент панели с изменяемыми размерами.
 */
export function ResizablePanel({
  notifyOnResize = false,
  ...props
}: PanelProps & { readonly notifyOnResize?: boolean }) {
  const { notifyResize } = useResizeContext();
  const { onResize } = props;

  const handleResize = useCallback(
    (size: PanelSize, id?: string | number, prevSize?: PanelSize) => {
      if (notifyOnResize) {
        notifyResize();
      }
      onResize?.(size, id, prevSize);
    },
    [notifyOnResize, notifyResize, onResize],
  );

  return (
    <Panel
      data-slot="resizable-panel"
      {...props}
      onResize={handleResize}
    />
  );
}

/**
 * Представляет компонент для изменения размеров панели.
 */
export function ResizableHandle({
  withHandle,
  className,
  ...props
}: SeparatorProps & {
  withHandle?: boolean;
}) {
  return (
    <Separator
      data-slot="resizable-handle"
      className={cn(styles.resizable_handle, className)}
      {...props}
    >
      {withHandle && (
        <div className={styles.handle_grip}>
          <DragHandleDotsIcon className={styles.grip_icon} />
        </div>
      )}
    </Separator>
  );
}
