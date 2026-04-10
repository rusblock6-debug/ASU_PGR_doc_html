import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import type { RouteTaskResponse } from '@/shared/api/types/trip-service';
import { cn } from '@/shared/lib/classnames-utils';
import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';
import { getRouteMain } from '@/shared/routes/router';

import { useRouteTaskActions } from '../../model/useRouteTaskActions';

import styles from './RouteTaskActionPanel.module.css';

const ACTION_CANCEL = 'action-cancel';
const ACTION_PAUSE = 'action-pause';
const ACTION_PRIMARY = 'action-primary';

/**
 * Пропсы панели действий для выбранного задания.
 */
interface RouteTaskActionPanelProps {
  readonly task: RouteTaskResponse;
}

/**
 * Вертикальная панель действий над маршрутом (отмена, пауза, приступить/завершить).
 */
export const RouteTaskActionPanel = ({ task }: RouteTaskActionPanelProps) => {
  const navigate = useNavigate();
  const { selectedId, setOnConfirm } = useKioskNavigation();
  const { primaryLabel, handleCancelTask, handlePause, handlePrimary, disabled, isLoading } = useRouteTaskActions(
    task,
    {
      onActivated: () => {
        void navigate(getRouteMain());
      },
    },
  );

  useEffect(() => {
    setOnConfirm(() => {
      if (disabled || isLoading) {
        return;
      }
      if (selectedId === ACTION_CANCEL) {
        void handleCancelTask();
        return;
      }
      if (selectedId === ACTION_PAUSE) {
        void handlePause();
        return;
      }
      if (selectedId === ACTION_PRIMARY) {
        void handlePrimary();
      }
    });
    return () => setOnConfirm(null);
  }, [disabled, isLoading, selectedId, setOnConfirm, handleCancelTask, handlePause, handlePrimary]);

  return (
    <div
      className={styles.root}
      role="group"
      aria-label="Действия по маршруту"
    >
      <button
        type="button"
        className={cn(styles.button, selectedId === ACTION_CANCEL && styles.button_selected)}
        disabled={disabled || isLoading}
        onClick={() => void handleCancelTask()}
      >
        ОТМЕНИТЬ
      </button>
      <button
        type="button"
        className={cn(styles.button, selectedId === ACTION_PAUSE && styles.button_selected)}
        disabled={disabled || isLoading}
        onClick={() => void handlePause()}
      >
        ПАУЗА
      </button>
      <button
        type="button"
        className={cn(styles.button, selectedId === ACTION_PRIMARY && styles.button_selected)}
        disabled={disabled || isLoading}
        onClick={() => void handlePrimary()}
      >
        {primaryLabel}
      </button>
    </div>
  );
};
