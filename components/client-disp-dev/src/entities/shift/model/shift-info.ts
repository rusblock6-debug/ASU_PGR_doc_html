/**
 * Представляет информацию о смене.
 */
export interface ShiftInfo {
  /** Возвращает номер смены. */
  readonly shiftNum: number;
  /** Возвращает дату смены. */
  readonly shiftDate: Date;
  /** Возвращает время начала смены. */
  readonly startTime: Date;
  /** Возвращает время окончания смены. */
  readonly endTime: Date;
}
