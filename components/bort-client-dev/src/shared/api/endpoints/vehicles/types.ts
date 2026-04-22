/** DTO техники из enterprise-service. */
export interface VehicleResponse {
  readonly id: number;
  readonly name: string;
  readonly [key: string]: unknown;
}
