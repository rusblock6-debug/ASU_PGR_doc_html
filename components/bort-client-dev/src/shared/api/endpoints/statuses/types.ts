/** Статус (простой) из enterprise-service. */
export interface StatusResponse {
  readonly id: number | string;
  readonly name: string;
  readonly display_name?: string;
  /** Код для POST /state/transition `new_state` (trip-service). */
  readonly system_name?: string;
  readonly organization_category_id?: number | string | null;
  readonly category_id?: number | string | null;
  readonly [key: string]: unknown;
}
