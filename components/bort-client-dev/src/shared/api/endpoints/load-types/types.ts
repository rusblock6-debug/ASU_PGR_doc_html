/** DTO типа груза из enterprise-service. */
export interface LoadTypeResponse {
  readonly id: number;
  readonly name: string;
  readonly density: number | null;
  readonly [key: string]: unknown;
}
