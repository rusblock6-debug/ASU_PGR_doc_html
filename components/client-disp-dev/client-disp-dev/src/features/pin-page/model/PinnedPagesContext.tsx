import { createContext, useContext } from 'react';

import type { AppRouteType } from '@/shared/routes/router';

import { type PageLayout, type PinnedPage } from './types/pinned';

interface PinnedPagesContextValue {
  pinnedPages: PinnedPage[];
  pinPage: (id: AppRouteType) => boolean;
  unpinPage: (id: AppRouteType) => void;
  updateLayout: (layouts: PageLayout[]) => void;
  isPinned: (id: AppRouteType) => boolean;
}

export const PinnedPagesContext = createContext<PinnedPagesContextValue | null>(null);

export function usePinnedPages() {
  const context = useContext(PinnedPagesContext);
  if (!context) {
    throw new Error('useWorkspace must be used within PinnedPagesProvider');
  }
  return context;
}
