import { RouteStatus, type RouteTaskStatus } from '@/shared/api/endpoints/route-tasks';
import QuestionCircleIcon from '@/shared/assets/icons/ic-question-circle.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { Tooltip } from '@/shared/ui/Tooltip';

import styles from './RouteStatusBadge.module.css';

/**
 * Конфигурация отображения для каждого статуса.
 */
export const routeStatusConfig: Record<
  RouteTaskStatus,
  {
    /** Текст для отображения. */
    readonly label: string;
    /** Текст для тултипа. */
    readonly tooltip: string;
    /** CSS-класс для стилизации. */
    readonly variant: 'default' | 'sent' | 'delivered' | 'active' | 'paused' | 'completed' | 'rejected';
  }
> = {
  [RouteStatus.EMPTY]: {
    label: 'К заполнению',
    tooltip: 'Задание готово к заполнению',
    variant: 'default',
  },
  [RouteStatus.SENT]: {
    label: 'Отправлено',
    tooltip: 'Задание отправлено на борт',
    variant: 'sent',
  },
  [RouteStatus.DELIVERED]: {
    label: 'Доставлено',
    tooltip: 'Задание доставлено на борт, оператор пока не приступил к работе',
    variant: 'delivered',
  },
  [RouteStatus.ACTIVE]: {
    label: 'В работе',
    tooltip: 'Оператор принял задание в работу',
    variant: 'active',
  },
  [RouteStatus.PAUSED]: {
    label: 'На паузе',
    tooltip: 'Работа над наряд-заданием приостановлена',
    variant: 'paused',
  },
  [RouteStatus.COMPLETED]: {
    label: 'Завершено',
    tooltip: 'Наряд-задание выполнено',
    variant: 'completed',
  },
  [RouteStatus.REJECTED]: {
    label: 'Отменено',
    tooltip: 'Наряд-задание отменено',
    variant: 'rejected',
  },
};

/**
 * Представляет свойства компонента RouteStatusBadge.
 */
interface RouteStatusBadgeProps {
  /** Статус маршрутного задания для отображения. */
  readonly status: RouteTaskStatus;
}

/**
 * Компонент для отображения статуса маршрутного задания.
 * Показывает текстовый статус с тултипом.
 */
export function RouteStatusBadge({ status = RouteStatus.EMPTY }: RouteStatusBadgeProps) {
  const config = routeStatusConfig[status];

  return (
    <p className={cn(styles.route_task_status, styles[`variant_${config.variant}`])}>
      <span>{config.label}</span>
      <Tooltip label={config.tooltip}>
        <QuestionCircleIcon />
      </Tooltip>
    </p>
  );
}
