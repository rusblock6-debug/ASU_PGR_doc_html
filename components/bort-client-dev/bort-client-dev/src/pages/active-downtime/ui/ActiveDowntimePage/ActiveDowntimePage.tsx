import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { ConfirmButton } from '@/widgets/kiosk-controls';

import { useSetVehicleStateTransitionMutation } from '@/shared/api';
import { cn } from '@/shared/lib/classnames-utils';
import { clearDowntimeSession, readDowntimeSession, type DowntimeSessionSnapshot } from '@/shared/lib/downtime-session';
import { useKioskAside } from '@/shared/lib/kiosk-aside';
import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';
import { getRouteVehicleStatus } from '@/shared/routes/router';
import { KioskBackButton } from '@/shared/ui/KioskBackButton';

import styles from './ActiveDowntimePage.module.css';

const KIOSK_FINISH_ID = 'active-downtime-finish';

/** Форматирует длительность в `ЧЧ:ММ:СС` для таймера простоя. */
function formatHms(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return [h, m, sec].map((n) => String(n).padStart(2, '0')).join(':');
}

/**
 * Экран активного простоя: локальный таймер и завершение с возвратом к предыдущему статусу.
 */
export const ActiveDowntimePage = () => {
  const navigate = useNavigate();
  const { setAsideLeft } = useKioskAside();
  const { setItemIds, setOnConfirm, selectedId } = useKioskNavigation();

  const [snapshot, setSnapshot] = useState<DowntimeSessionSnapshot | null>(() => readDowntimeSession());
  const [elapsedSec, setElapsedSec] = useState(0);

  const [setTransition, { isLoading: isFinishing }] = useSetVehicleStateTransitionMutation();

  useEffect(() => {
    if (!snapshot) {
      void navigate(getRouteVehicleStatus(), { replace: true });
    }
  }, [snapshot, navigate]);

  useEffect(() => {
    if (!snapshot) {
      return;
    }
    const tick = () => {
      setElapsedSec(Math.floor((Date.now() - snapshot.startedAt) / 1000));
    };
    tick();
    const id = window.setInterval(tick, 1000);
    return () => {
      window.clearInterval(id);
    };
  }, [snapshot]);

  const handleFinish = () => {
    if (!snapshot || isFinishing) {
      return;
    }
    void setTransition({
      new_state: snapshot.prevStatus,
      reason: 'manual',
      comment: 'Окончание простоя',
    })
      .unwrap()
      .then(() => {
        clearDowntimeSession();
        void navigate(getRouteVehicleStatus());
      });
  };

  const handleFinishRef = useRef(handleFinish);
  handleFinishRef.current = handleFinish;

  useEffect(() => {
    setItemIds([KIOSK_FINISH_ID]);
  }, [setItemIds]);

  useEffect(() => {
    setOnConfirm(() => {
      if (selectedId === KIOSK_FINISH_ID) {
        handleFinishRef.current();
      }
    });
    return () => {
      setOnConfirm(null);
    };
  }, [selectedId, setOnConfirm]);

  useEffect(() => {
    setAsideLeft(
      <>
        <KioskBackButton onClick={() => void navigate(getRouteVehicleStatus())} />
        <ConfirmButton disabled={isFinishing || !snapshot} />
      </>,
    );
    return () => {
      setAsideLeft(null);
    };
  }, [setAsideLeft, navigate, isFinishing, snapshot]);

  useEffect(() => {
    const onFocus = () => {
      setSnapshot(readDowntimeSession());
    };
    window.addEventListener('focus', onFocus);
    return () => {
      window.removeEventListener('focus', onFocus);
    };
  }, []);

  if (!snapshot) {
    return null;
  }

  return (
    <div className={styles.page}>
      <div className={styles.main}>
        <h1 className={styles.prev_title}>{snapshot.reasonLabel}</h1>
        <div
          className={styles.timer}
          aria-live="polite"
        >
          {formatHms(elapsedSec)}
        </div>
        <p className={styles.timer_caption}>Время простоя</p>
      </div>
      <button
        type="button"
        className={cn(styles.finish_btn, selectedId === KIOSK_FINISH_ID && styles.finish_btn_selected)}
        disabled={isFinishing}
        aria-label="Завершить простой"
        onClick={handleFinish}
      >
        ЗАВЕРШИТЬ ПРОСТОЙ
      </button>
    </div>
  );
};
