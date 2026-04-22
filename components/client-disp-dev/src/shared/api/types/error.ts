import { hasValue } from '@/shared/lib/has-value';

/** Элемент валидационной ошибки Pydantic (422). */
export interface ValidationErrorDetail {
  /** Путь к полю, вызвавшему ошибку (например, `["body", "from_node_id"]`). */
  readonly loc: readonly (string | number)[];
  /** Человекочитаемое описание ошибки. */
  readonly msg: string;
  /** Машинный идентификатор типа ошибки (например, `"value_error"`, `"missing"`). */
  readonly type: string;
}

/**
 * Тело ошибки FastAPI.
 *
 * - Pydantic-валидация (422) → `detail` — массив {@link ValidationErrorDetail}.
 * - `HTTPException` (4xx) → `detail` — строка с описанием ошибки.
 */
export interface HTTPError {
  /** Описание ошибки: строка для HTTPException, массив для Pydantic-валидации. */
  readonly detail: string | readonly ValidationErrorDetail[];
}

/** Извлекает типизированное тело ошибки из ответа `fetchBaseQuery`. */
export const toHTTPError = (response: { data?: unknown }): HTTPError => response.data as HTTPError;

/** Проверяет, является ли значение ошибкой FastAPI с полем `detail`. */
export const isHTTPError = (value: unknown): value is HTTPError =>
  typeof value === 'object' && hasValue(value) && 'detail' in value;
