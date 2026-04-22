/**
 * Типы статусов генерации чанков.
 */
type PlaybackStatus = 'processing' | 'ready' | 'error';

/**
 * Представляет модель данных для запроса истории оборудования.
 */
export interface MapPlayerPlaybackRequest {
  /** Возвращает дату начала воспроизведения. */
  readonly start_date: string;
  /** Возвращает дату окончания воспроизведения. */
  readonly end_date: string;
  /** Возвращает список идентификаторов оборудования. */
  readonly vehicle_ids: readonly number[];
}

/**
 * Представляет модель данных получаемую по запросу истории оборудования.
 */
export interface MapPlayerPlayback {
  /** Возвращает уникальный хэш воспроизведения. */
  readonly hash: string;
  /** Возвращает текущий статус генерации чанков. */
  readonly status: PlaybackStatus;
  /** Возвращает количество уже сгенерированных чанков. */
  readonly chunk_count: number;
  /** Возвращает ожидаемое общее количество чанков. */
  readonly total_chunk_counts: number;
  /** Возвращает длительность одного чанка в секундах. */
  readonly chunk_duration_sec: number;
  /** Возвращает дату начала воспроизведения. */
  readonly start_date: string;
  /** Возвращает дату окончания воспроизведения. */
  readonly end_date: string;
  /** Возвращает список идентификаторов оборудования. */
  readonly vehicle_ids: readonly number[];
}

/**
 * Представляет модель записи в истории оборудования.
 */
export interface MapPlayerPlaybackItem {
  /** Возвращает идентификатор оборудования. */
  readonly vehicle_id: number;
  /** Возвращает временную отметку. */
  readonly timestamp: string;
  /** Возвращает координату широты. */
  readonly lat: number;
  /** Возвращает координату долготы. */
  readonly lon: number;
  /** Возвращает высоту. */
  readonly height: number | null;
  /** Возвращает скорость. */
  readonly speed: number | null;
  /** Возвращает остаток топлива. */
  readonly fuel: number | null;
}

/**
 * Представляет модель чанка истории оборудования.
 */
export interface MapPlayerPlaybackChunkResponse {
  /** Возвращает уникальный хэш воспроизведения. */
  readonly hash: string;
  /** Возвращает индекс чанка. */
  readonly chunk_index: number;
  /** Возвращает общее количество чанков. */
  readonly total_chunks: number;
  /** Возвращает список записей в чанке. */
  readonly data: readonly MapPlayerPlaybackItem[];
}
