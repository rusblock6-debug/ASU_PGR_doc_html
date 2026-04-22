/** Категория статусов из enterprise-service. */
export interface OrganizationCategoryResponse {
  readonly id: number | string;
  readonly name: string;
  readonly display_name?: string;
  readonly [key: string]: unknown;
}
