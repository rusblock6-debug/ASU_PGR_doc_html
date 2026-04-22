import { forwardRef, useImperativeHandle, useRef, type ReactNode } from 'react';

import { RouteTaskRow } from '@/entities/route-task';

import type { RouteTaskResponse } from '@/shared/api/endpoints/tasks';

import styles from './RouteTaskList.module.css';

/**
 * Пропсы таблицы маршрутных заданий.
 */
interface RouteTaskListProps {
  /** Список маршрутных заданий смены. */
  readonly tasks: RouteTaskResponse[];
  /** Индекс выбранной строки. */
  readonly selectedIndex: number;
  /** Колбэк выбора строки по индексу. */
  readonly onRowSelect: (index: number) => void;
  /** Слот для тулбара над таблицей. */
  readonly toolbar?: ReactNode;
}

/**
 * Императивный API: прокрутка к строке по индексу (kiosk-стрелки).
 */
export interface RouteTaskListHandle {
  readonly scrollToRowIndex: (index: number) => void;
}

/**
 * Таблица маршрутов текущей смены.
 */
export const RouteTaskList = forwardRef<RouteTaskListHandle, RouteTaskListProps>(function RouteTaskList(
  { tasks, selectedIndex, onRowSelect, toolbar },
  ref,
) {
  const rowRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useImperativeHandle(
    ref,
    () => ({
      scrollToRowIndex: (index: number) => {
        rowRefs.current[index]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      },
    }),
    [],
  );

  return (
    <div className={styles.wrapper}>
      {toolbar ? <div className={styles.toolbar}>{toolbar}</div> : null}
      <div
        className={styles.header}
        role="row"
      >
        <span>№</span>
        <span>Начало маршрута</span>
        <span>Конец маршрута</span>
        <span>Рейсы</span>
        <span>Вес, т</span>
        <span>Объём, м³</span>
        <span>Груз</span>
        <span>Статус</span>
      </div>
      <div className={styles.scroll}>
        {tasks.length === 0 ? (
          <div className={styles.empty}>Нет маршрутов в наряде</div>
        ) : (
          tasks.map((task, index) => (
            <RouteTaskRow
              key={task.id}
              rowRef={(el) => {
                rowRefs.current[index] = el;
              }}
              index={index}
              task={task}
              isSelected={index === selectedIndex}
              onSelect={() => onRowSelect(index)}
            />
          ))
        )}
      </div>
    </div>
  );
});
