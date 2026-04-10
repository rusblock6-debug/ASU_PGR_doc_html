const KEY_PREV = 'downtime.prevStatusBeforeIdle';
const KEY_STARTED = 'downtime.startedAt';
const KEY_REASON = 'downtime.reasonLabel';

/** Сохраняет код операционного статуса до входа в простой (для возврата после idle). */
export function savePrevStatusBeforeIdle(code: string) {
  sessionStorage.setItem(KEY_PREV, code);
}

/** Читает сохранённый код статуса до простоя (если есть). */
export function readPrevStatusBeforeIdle() {
  return sessionStorage.getItem(KEY_PREV);
}

/** После успешного POST в idle — фиксирует момент старта таймера и текст причины. */
export function startDowntimeSession(reasonLabel: string) {
  sessionStorage.setItem(KEY_STARTED, String(Date.now()));
  sessionStorage.setItem(KEY_REASON, reasonLabel);
}

/** Снимок данных экрана активного простоя из `sessionStorage`. */
export interface DowntimeSessionSnapshot {
  readonly prevStatus: string;
  readonly startedAt: number;
  readonly reasonLabel: string;
}

/** Возвращает полный снимок простоя или `null`, если данные неполные. */
export function readDowntimeSession() {
  const prev = sessionStorage.getItem(KEY_PREV);
  const startedRaw = sessionStorage.getItem(KEY_STARTED);
  const reason = sessionStorage.getItem(KEY_REASON);
  if (!prev || !startedRaw || !reason) {
    return null;
  }
  const startedAt = Number(startedRaw);
  if (!Number.isFinite(startedAt)) {
    return null;
  }
  return { prevStatus: prev, startedAt, reasonLabel: reason };
}

/** Удаляет ключи простоя из `sessionStorage`. */
export function clearDowntimeSession() {
  sessionStorage.removeItem(KEY_PREV);
  sessionStorage.removeItem(KEY_STARTED);
  sessionStorage.removeItem(KEY_REASON);
}
