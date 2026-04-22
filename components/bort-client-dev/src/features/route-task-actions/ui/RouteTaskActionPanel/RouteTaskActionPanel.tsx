import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import type { RouteTaskResponse } from '@/shared/api/endpoints/tasks';
import { cn } from '@/shared/lib/classnames-utils';
import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';
import { getRouteMain } from '@/shared/routes/router';

import { ACTION } from '../../lib/kiosk-item-ids';
import { useRouteTaskActions } from '../../model/useRouteTaskActions';

import styles from './RouteTaskActionPanel.module.css';

/**
 * Пропсы панели действий для выбранного задания.
 */
interface RouteTaskActionPanelProps {
  /** Маршрутное задание, для которого отображаются действия. */
  readonly task: RouteTaskResponse;
}

/**
 * Вертикальная панель действий над маршрутом (приступить, пауза, завершить, отменить).
 */
export const RouteTaskActionPanel = ({ task }: RouteTaskActionPanelProps) => {
  const navigate = useNavigate();
  const { selectedId, setOnConfirm } = useKioskNavigation();
  const { handleStart, handlePause, handleComplete, handleCancel, disabledMap } = useRouteTaskActions(task, {
    onStarted: () => {
      void navigate(getRouteMain());
    },
  });

  useEffect(() => {
    setOnConfirm(() => {
      if (selectedId === ACTION.START && !disabledMap.start) {
        void handleStart();
        return;
      }
      if (selectedId === ACTION.CANCEL && !disabledMap.cancel) {
        void handleCancel();
        return;
      }
      if (selectedId === ACTION.PAUSE && !disabledMap.pause) {
        void handlePause();
        return;
      }
      if (selectedId === ACTION.COMPLETE && !disabledMap.complete) {
        void handleComplete();
      }
    });
    return () => setOnConfirm(null);
  }, [selectedId, setOnConfirm, handleStart, handleCancel, handlePause, handleComplete, disabledMap]);

  return (
    <div
      className={styles.root}
      role="group"
      aria-label="Действия по маршруту"
    >
      <button
        type="button"
        className={cn(styles.button, selectedId === ACTION.START && styles.button_selected)}
        disabled={disabledMap.start}
        onClick={() => void handleStart()}
      >
        ПРИСТУПИТЬ
      </button>
      <button
        type="button"
        className={cn(styles.button, selectedId === ACTION.PAUSE && styles.button_selected)}
        disabled={disabledMap.pause}
        onClick={() => void handlePause()}
      >
        НА ПАУЗУ
      </button>
      <button
        type="button"
        className={cn(styles.button, selectedId === ACTION.COMPLETE && styles.button_selected)}
        disabled={disabledMap.complete}
        onClick={() => void handleComplete()}
      >
        ЗАВЕРШИТЬ
      </button>
      <button
        type="button"
        className={cn(styles.button, selectedId === ACTION.CANCEL && styles.button_selected)}
        disabled={disabledMap.cancel}
        onClick={() => void handleCancel()}
      >
        ОТМЕНИТЬ
      </button>
    </div>
  );
};
