import { createContext, useContext } from 'react';

import type { AppRouteType } from '@/shared/routes/router';

interface FavoritePagesContextValue {
  favoritePages: AppRouteType[];
  addToFavorites: (id: AppRouteType) => void;
  removeFromFavorites: (id: AppRouteType) => void;
  isFavorite: (id: AppRouteType) => boolean;
}

export const FavoritePagesContext = createContext<FavoritePagesContextValue | null>(null);

export function useFavoritePages() {
  const context = useContext(FavoritePagesContext);
  if (!context) {
    throw new Error('useFavoritePages must be used within FavoritePagesProvider');
  }
  return context;
}
