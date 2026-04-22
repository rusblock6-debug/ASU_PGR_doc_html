/** DTO тега (места) из graph-service GET /api/tags/:id */
export interface TagResponse {
  readonly id?: string | number;
  readonly name: string;
  readonly [key: string]: unknown;
}
