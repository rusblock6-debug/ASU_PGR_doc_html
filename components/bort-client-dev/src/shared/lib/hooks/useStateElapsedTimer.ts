import { useEffect, useRef, useState } from 'react';
import { useSelector } from 'react-redux';

import { selectStateChangedAt, selectVehicleState } from '@/shared/api/endpoints/vehicle-state';
import type { VehicleState } from '@/shared/api/types/vehicle-events';

const INTERVAL_MS = 1_000;

const pad = (n: number) => String(n).padStart(2, '0');

/** Форматирует длительность в `HH:MM:SS`. */
const formatElapsed = (ms: number) => {
  const totalSeconds = Math.max(0, Math.floor(ms / 1_000));
  const h = Math.floor(totalSeconds / 3_600);
  const m = Math.floor((totalSeconds % 3_600) / 60);
  const s = totalSeconds % 60;
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
};

/** Возвращает `HH:MM:SS` — время с момента входа в текущий статус борта (не сбрасывается при повторных `state_event` с тем же `status` и новым `timestamp`). */
export const useStateElapsedTimer = () => {
  const stateStatus = useSelector(selectVehicleState);
  const changedAt = useSelector(selectStateChangedAt);
  const [elapsed, setElapsed] = useState<string | null>(null);
  const prevStatusRef = useRef<VehicleState | null | undefined>(undefined);
  const originMsRef = useRef<number | null>(null);

  useEffect(() => {
    const tsMs = changedAt ? new Date(changedAt).getTime() : null;
    const validTs = tsMs != null && !Number.isNaN(tsMs);

    if (stateStatus !== prevStatusRef.current) {
      prevStatusRef.current = stateStatus;
      originMsRef.current = validTs ? tsMs : null;
    } else if (originMsRef.current == null && validTs) {
      originMsRef.current = tsMs;
    }

    const origin = originMsRef.current;
    if (origin == null) {
      setElapsed(null);
      return;
    }

    const tick = () => {
      setElapsed(formatElapsed(Date.now() - origin));
    };

    tick();
    const id = setInterval(tick, INTERVAL_MS);
    return () => clearInterval(id);
  }, [stateStatus, changedAt]);

  return elapsed;
};
