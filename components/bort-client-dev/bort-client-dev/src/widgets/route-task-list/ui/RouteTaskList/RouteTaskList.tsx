import type { ReactNode } from 'react';

import { RouteTaskRow } from '@/entities/route-task';

import type { RouteTaskResponse } from '@/shared/api/types/trip-service';

import styles from './RouteTaskList.module.css';

/**
 * Пропсы таблицы маршрутных заданий.
 */
interface RouteTaskListProps {
  readonly tasks: RouteTaskResponse[];
  readonly selectedIndex: number;
  readonly onRowSelect: (index: number) => void;
  readonly toolbar?: ReactNode;
}

/**
 * Таблица маршрутов текущей смены.
 */
export const RouteTaskList = ({ tasks, selectedIndex, onRowSelect, toolbar }: RouteTaskListProps) => (
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
    {tasks.length === 0 ? (
      <div className={styles.empty}>Нет маршрутов в наряде</div>
    ) : (
      tasks.map((task, index) => (
        <RouteTaskRow
          key={task.id}
          index={index}
          task={task}
          isSelected={index === selectedIndex}
          onSelect={() => onRowSelect(index)}
        />
      ))
    )}
  </div>
);
