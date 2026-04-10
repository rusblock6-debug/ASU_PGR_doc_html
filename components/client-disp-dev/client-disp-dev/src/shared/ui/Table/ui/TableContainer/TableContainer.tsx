'use no memo';

import type { DragEndEvent } from '@dnd-kit/core';
import { closestCenter, DndContext, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { restrictToHorizontalAxis } from '@dnd-kit/modifiers';
import type { ReactNode, RefObject } from 'react';

import { cn } from '@/shared/lib/classnames-utils';

import styles from './TableContainer.module.css';

interface TableContainerProps {
  readonly children: ReactNode;
  readonly handleDragEnd: (event: DragEndEvent) => void;
  readonly className?: string;
  readonly tableContainerRef: RefObject<HTMLDivElement | null>;
}

export function TableContainer({ children, handleDragEnd, className, tableContainerRef }: TableContainerProps) {
  const sensors = useSensors(useSensor(PointerSensor), useSensor(KeyboardSensor, {}));

  return (
    <div
      className={cn(styles.container, className)}
      ref={tableContainerRef}
    >
      <DndContext
        collisionDetection={closestCenter}
        modifiers={[restrictToHorizontalAxis]}
        onDragEnd={handleDragEnd}
        sensors={sensors}
        autoScroll={false}
      >
        {children}
      </DndContext>
    </div>
  );
}
