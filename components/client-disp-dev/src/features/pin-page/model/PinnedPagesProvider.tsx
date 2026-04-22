import { type ReactNode, useCallback, useEffect, useMemo, useState } from 'react';

import { getTitleById } from '@/shared/routes/get-title-by-id';
import type { AppRouteType } from '@/shared/routes/router';

import { applyDefaultLayout, calculateNewLayout, hasManualChanges } from '../lib/calculate-layout';
import { hydratePinnedPage } from '../lib/page-utils';

import { PinnedPagesContext } from './PinnedPagesContext';
import { type PageLayout, type PinnedPage, type StoredPinnedPage } from './types/pinned';

const STORAGE_KEY = 'asu-gtk-pinned-pages';

export function PinnedPagesProvider({ children }: { readonly children: ReactNode }) {
  const [pinnedPages, setPinnedPages] = useState<PinnedPage[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) return [];
      const storedPages: StoredPinnedPage[] = JSON.parse(stored);
      return storedPages.map(hydratePinnedPage);
    } catch {
      return [];
    }
  });

  useEffect(() => {
    const toStore: StoredPinnedPage[] = pinnedPages.map((page) => ({
      id: page.id,
      layout: page.layout,
    }));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toStore));
  }, [pinnedPages]);

  const pinPage = useCallback(
    (id: AppRouteType): boolean => {
      if (pinnedPages.some((page) => page.id === id)) {
        return false;
      }

      setPinnedPages((prev) => {
        const manualChanges = hasManualChanges(prev);

        // Если не было ручных изменений, сначала применяем дефолтную схему к существующим
        let basePages = prev;
        if (!manualChanges && prev.length > 0 && prev.length <= 4) {
          basePages = applyDefaultLayout(prev);
        }

        const newPages = [
          ...basePages,
          {
            id,
            route: id,
            title: getTitleById(id),
            layout: calculateNewLayout(basePages),
          },
        ];

        // Если не было ручных изменений и элементов <= 4, применяем дефолтную схему
        if (!manualChanges && newPages.length <= 4) {
          return applyDefaultLayout(newPages);
        }

        // Иначе возвращаем с новым элементом внизу
        return newPages;
      });

      return true;
    },
    [pinnedPages],
  );

  const unpinPage = useCallback((id: AppRouteType) => {
    setPinnedPages((prev) => prev.filter((page) => page.id !== id));
  }, []);

  const updateLayout = useCallback((layouts: PageLayout[]) => {
    setPinnedPages((prev) =>
      prev.map((page, index) => ({
        ...page,
        layout: layouts[index] || page.layout,
      })),
    );
  }, []);

  const isPinned = useCallback(
    (id: AppRouteType) => {
      return pinnedPages.some((page) => page.id === id);
    },
    [pinnedPages],
  );

  const value = useMemo(
    () => ({
      pinnedPages,
      pinPage,
      unpinPage,
      updateLayout,
      isPinned,
    }),
    [pinnedPages, pinPage, unpinPage, updateLayout, isPinned],
  );

  return <PinnedPagesContext.Provider value={value}>{children}</PinnedPagesContext.Provider>;
}
