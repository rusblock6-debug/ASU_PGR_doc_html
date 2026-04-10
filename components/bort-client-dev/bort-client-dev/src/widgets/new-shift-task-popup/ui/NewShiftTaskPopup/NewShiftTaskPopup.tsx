import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

import { getCargoLabel, getPlaceLabelFromRouteData, useRouteTaskPlaceNames } from '@/entities/route-task';

import type { RouteTaskResponse } from '@/shared/api/types/trip-service';
import { NO_DATA } from '@/shared/lib/constants';
import { useCargoMetrics } from '@/shared/lib/hooks/useCargoMetrics';
import { useRouteNodeMetrics } from '@/shared/lib/hooks/useRouteNodeMetrics';
import { getRouteStreamDistanceKmParts, getRouteStreamDurationMinutesCeilParts } from '@/shared/lib/route-stream';

import styles from './NewShiftTaskPopup.module.css';

const AUTO_ACCEPT_SECONDS = 60;
const TIMER_R = 52;
const TIMER_C = 2 * Math.PI * TIMER_R;

/**
 * Пропсы блокирующего попапа «Новое задание».
 */
interface NewShiftTaskPopupProps {
  readonly routeTask: RouteTaskResponse;
  readonly onConfirm: () => void | Promise<void>;
  readonly onReject: () => void | Promise<void>;
  readonly isLoading: boolean;
}

/**
 * Модалка нового маршрутного задания: автопринятие через 60 с, только кнопки или таймер закрывают.
 */
export const NewShiftTaskPopup = ({ routeTask, onConfirm, onReject, isLoading }: NewShiftTaskPopupProps) => {
  const [remainingSec, setRemainingSec] = useState(AUTO_ACCEPT_SECONDS);
  const autoFiredRef = useRef(false);
  const userActedRef = useRef(false);
  const onConfirmRef = useRef(onConfirm);
  onConfirmRef.current = onConfirm;

  const { placeAName, placeBName } = useRouteTaskPlaceNames(routeTask.place_a_id, routeTask.place_b_id);
  const { cargoTypeName } = useCargoMetrics(routeTask.place_b_id);
  const { distanceMeters, durationSeconds } = useRouteNodeMetrics(routeTask.place_a_id, routeTask.place_b_id);

  const startLabel = getPlaceLabelFromRouteData(routeTask.place_a_id, routeTask.route_data, 'place_a_name', placeAName);
  const endLabel = getPlaceLabelFromRouteData(routeTask.place_b_id, routeTask.route_data, 'place_b_name', placeBName);
  const cargoLabel = getCargoLabel(routeTask.type_task, routeTask.route_data, cargoTypeName);

  const distanceParts = getRouteStreamDistanceKmParts(distanceMeters);
  const durationParts = getRouteStreamDurationMinutesCeilParts(durationSeconds);

  const progressRatio = remainingSec / AUTO_ACCEPT_SECONDS;
  const dashOffset = TIMER_C * (1 - progressRatio);

  useEffect(() => {
    autoFiredRef.current = false;
    userActedRef.current = false;
    setRemainingSec(AUTO_ACCEPT_SECONDS);
  }, [routeTask.id]);

  useEffect(() => {
    const id = window.setInterval(() => {
      setRemainingSec((prev) => (prev <= 1 ? 0 : prev - 1));
    }, 1000);
    return () => window.clearInterval(id);
  }, [routeTask.id]);

  useEffect(() => {
    if (remainingSec !== 0 || autoFiredRef.current || isLoading || userActedRef.current) {
      return;
    }
    autoFiredRef.current = true;
    void Promise.resolve(onConfirmRef.current());
  }, [remainingSec, isLoading]);

  useEffect(() => {
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, []);

  const weightText = routeTask.weight != null ? `${routeTask.weight} т` : NO_DATA.LONG_DASH;
  const volumeText = routeTask.volume != null ? `${routeTask.volume} м³` : NO_DATA.LONG_DASH;

  return createPortal(
    <div
      className={styles.backdrop}
      role="dialog"
      aria-modal="true"
      aria-labelledby="new-shift-task-title"
    >
      <div className={styles.card}>
        <div className={styles.left}>
          <div className={styles.header_kicker}>
            <span className={styles.header_dot} />
            <span id="new-shift-task-title">Новое задание</span>
          </div>
          <button
            type="button"
            className={styles.reject_btn}
            disabled={isLoading}
            onClick={() => {
              userActedRef.current = true;
              void onReject();
            }}
          >
            Отказаться
          </button>
          <div className={styles.timer_wrap}>
            <svg
              className={styles.timer_svg}
              width={120}
              height={120}
              viewBox="0 0 120 120"
              aria-hidden
            >
              <circle
                className={styles.timer_track}
                cx={60}
                cy={60}
                r={TIMER_R}
              />
              <circle
                className={styles.timer_progress}
                transform="rotate(-90 60 60)"
                cx={60}
                cy={60}
                r={TIMER_R}
                strokeDasharray={`${TIMER_C} ${TIMER_C}`}
                strokeDashoffset={dashOffset}
              />
            </svg>
            <div className={styles.timer_center}>
              <span className={styles.timer_secs}>{remainingSec} с</span>
              <span className={styles.timer_hint}>Автопринятие</span>
            </div>
          </div>
          <button
            type="button"
            className={styles.confirm_btn}
            disabled={isLoading}
            onClick={() => {
              userActedRef.current = true;
              void onConfirm();
            }}
          >
            Подтвердить
          </button>
        </div>
        <div className={styles.right}>
          <div className={styles.field}>
            <span className={styles.label}>Начало маршрута</span>
            <span className={styles.value}>{startLabel}</span>
          </div>
          <div className={styles.field}>
            <span className={styles.label}>Конец маршрута</span>
            <span className={styles.value}>{endLabel}</span>
          </div>
          <div className={styles.metrics_row}>
            <div className={styles.metric}>
              <span className={styles.label}>Расстояние</span>
              <span className={styles.metric_val}>
                {distanceParts ? (
                  <>
                    <span className={styles.metric_tilde}>~</span>
                    {distanceParts.value} {distanceParts.unit}
                  </>
                ) : (
                  NO_DATA.LONG_DASH
                )}
              </span>
            </div>
            <div className={styles.metric}>
              <span className={styles.label}>Время в пути</span>
              <span>
                {durationParts ? (
                  <>
                    <span className={styles.metric_tilde}>~</span>
                    <span className={styles.metric_val_accent}>{durationParts.value}</span>{' '}
                    <span className={styles.metric_val}>{durationParts.unit}</span>
                  </>
                ) : (
                  <span className={styles.metric_val}>{NO_DATA.LONG_DASH}</span>
                )}
              </span>
            </div>
            <div className={styles.metric}>
              <span className={styles.label}>Рейсы</span>
              <span className={styles.metric_val}>{routeTask.planned_trips_count}</span>
            </div>
          </div>
          <div className={styles.metrics_row_2}>
            <div className={styles.metric}>
              <span className={styles.label}>Масса</span>
              <span className={styles.metric_val}>{weightText}</span>
            </div>
            <div className={styles.metric}>
              <span className={styles.label}>Объём</span>
              <span className={styles.metric_val}>{volumeText}</span>
            </div>
          </div>
          <div className={styles.field}>
            <span className={styles.label}>Груз</span>
            <span className={styles.value}>{cargoLabel}</span>
          </div>
          {routeTask.message ? <div className={styles.message_block}>{routeTask.message}</div> : null}
        </div>
      </div>
    </div>,
    document.body,
  );
};
