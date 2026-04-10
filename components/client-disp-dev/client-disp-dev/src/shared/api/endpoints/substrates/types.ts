import type { Pagination } from '@/shared/api/types';

/** Центр подложки. */
export interface Center {
  /** X координата центра подложки. */
  readonly x: number;
  /** Y координата центра подложки. */
  readonly y: number;
}
/** DTO подложки, как приходит из API. */
export interface SubstrateResponse {
  /** Возвращает дату создания. */
  readonly created_at: string;
  /** Возвращает дату изменения. */
  readonly updated_at: string;
  /** Возвращает идентификатор. */
  readonly id: number;
  /** Возвращает идентификатор горизонта. */
  readonly horizon_id: number | null;
  /** Возвращает оригинальное имя файла. */
  readonly original_filename: string;
  /** Возвращает путь к файлу в хранилище S3. */
  readonly path_s3: string;
  /** Возвращает параметр прозрачности. */
  readonly opacity: number;
  /** Возвращает данные о центре. */
  readonly center: Center;
}
/** Подложка с дополнительной ссылкой на SVG. */
export interface SubstrateWithSvgResponse extends SubstrateResponse {
  readonly svg_link: string;
}
/** Ответ API со списком подложек. */
export interface SubstrateListResponse extends Pagination {
  readonly items: readonly SubstrateResponse[];
}

/** Патч для обновления подложки. */
export interface SubstrateUpdate {
  /** Идентификатор горизонта. */
  readonly horizon_id?: number | null;
  /** Параметр прозрачности подложки. */
  readonly opacity?: number | null;
  /** Центр подложки. */
  readonly center?: Center | null;
}
/** Пэйлоад для создания подложки. */
export interface CreateSubstratePayload {
  /** Файл для загрузки. */
  readonly file: File;
  /** Идентификатор горизонта. */
  readonly horizon_id?: number | null;
  /** Параметр прозрачности подложки. */
  readonly opacity?: number;
  /** Центр подложки. */
  readonly center?: Center | null;
}
/** Пэйлоад для перезаливки файла подложки. */
export interface RefreshSubstrateFilePayload {
  /** Идентификатор подложки. */
  readonly id: number;
  /** Файл для загрузки. */
  readonly file: File;
}
