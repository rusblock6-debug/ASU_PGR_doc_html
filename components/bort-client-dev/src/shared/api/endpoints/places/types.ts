/** DTO места из graph-service. */
export interface PlaceResponse {
  readonly id: number;
  readonly name: string;
  readonly cargo_type: number | null;
  readonly node_id?: number | null;
  readonly location?: { lon: number; lat: number } | null;
  readonly [key: string]: unknown;
}
