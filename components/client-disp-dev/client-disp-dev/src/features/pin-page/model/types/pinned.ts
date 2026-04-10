import type { AppRouteType } from '@/shared/routes/router';

export interface PageLayout {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface PinnedPage {
  id: AppRouteType;
  route: AppRouteType;
  title: string;
  layout: PageLayout;
}

export interface StoredPinnedPage {
  id: AppRouteType;
  layout: PageLayout;
}
