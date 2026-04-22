import type { CycleStateHistory } from '../state-history';

/** Представляет сообщение об изменении статуса. */
export interface StreamStateTransitionMessage extends CycleStateHistory {
  /** Возвращает тип события. */
  readonly event_type: 'state_transition';
}

/** Представляет сообщение об изменении истории статусов. */
export interface StreamStateHistoryChangedMessage {
  /** Возвращает тип события. */
  readonly event_type: 'history_changed';
  /** Возвращает идентификатор транспортного средства. */
  readonly vehicle_id: number;
  /** Возвращает дату смены. */
  readonly shift_date: string;
  /** Возвращает номер смены. */
  readonly shift_num: number;
}

/** Представляет типы сообщений, получаемых в стриме. */
export type StreamAllMessage = StreamStateTransitionMessage | StreamStateHistoryChangedMessage;

/**
 * Сужает тип сообщения до сообщения об изменении статуса транспортного средства.
 *
 * @param streamMessage сообщение полученное в стриме.
 */
export function isStreamStateTransitionMessage(
  streamMessage: StreamAllMessage,
): streamMessage is StreamStateTransitionMessage {
  return streamMessage.event_type === 'state_transition';
}

/**
 * Сужает тип сообщения до сообщения об изменении истории статусов транспортных средств.
 *
 * @param streamMessage сообщение полученное в стриме.
 */
export function isStreamStateHistoryChangedMessage(
  streamMessage: StreamAllMessage,
): streamMessage is StreamStateHistoryChangedMessage {
  return streamMessage.event_type === 'history_changed';
}
