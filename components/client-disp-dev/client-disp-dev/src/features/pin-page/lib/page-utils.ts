import { getTitleById } from '@/shared/routes/get-title-by-id';

import type { PinnedPage, StoredPinnedPage } from '../model/types/pinned';

/**
 * Восстанавливает полный объект PinnedPage из минимальных данных.
 *
 * @param stored минимальные данные из localStorage {id, layout}.
 * @returns полный объект {id, route, title, layout}.
 */
export function hydratePinnedPage(stored: StoredPinnedPage): PinnedPage {
  return {
    id: stored.id,
    route: stored.id, // route === id
    title: getTitleById(stored.id),
    layout: stored.layout,
  };
}
