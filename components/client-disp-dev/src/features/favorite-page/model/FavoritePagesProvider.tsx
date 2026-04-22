import { type ReactNode, useCallback, useEffect, useMemo, useState } from 'react';

import type { AppRouteType } from '@/shared/routes/router';

import { FavoritePagesContext } from './FavoritePagesContext';

const STORAGE_KEY = 'asu-gtk-favorite-pages';

export function FavoritePagesProvider({ children }: { readonly children: ReactNode }) {
  const [favoritePages, setFavoritePages] = useState<AppRouteType[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) return [];
      return JSON.parse(stored) as AppRouteType[];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(favoritePages));
  }, [favoritePages]);

  const addToFavorites = useCallback((id: AppRouteType) => {
    setFavoritePages((prev) => {
      if (prev.includes(id)) {
        return prev;
      }
      return [...prev, id];
    });
  }, []);

  const removeFromFavorites = useCallback((id: AppRouteType) => {
    setFavoritePages((prev) => prev.filter((pageId) => pageId !== id));
  }, []);

  const isFavorite = useCallback(
    (id: AppRouteType) => {
      return favoritePages.includes(id);
    },
    [favoritePages],
  );

  const value = useMemo(
    () => ({
      favoritePages,
      addToFavorites,
      removeFromFavorites,
      isFavorite,
    }),
    [favoritePages, addToFavorites, removeFromFavorites, isFavorite],
  );

  return <FavoritePagesContext.Provider value={value}>{children}</FavoritePagesContext.Provider>;
}
