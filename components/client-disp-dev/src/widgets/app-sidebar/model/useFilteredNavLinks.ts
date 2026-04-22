import { useMemo } from 'react';

import { selectUserPermissions } from '@/entities/user';

import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { type NavLinks, navLinks } from '@/shared/routes/navigation';
import { getRoutePermission } from '@/shared/routes/route-permissions';

/** Проверяет видимость пункта меню по доступам пользователя. */
const isItemVisible = (
  item: NonNullable<NavLinks['items']>[number],
  permissions: ReturnType<typeof selectUserPermissions>,
) => {
  const permissionName = item.key ? getRoutePermission(item.key) : undefined;
  if (!permissionName) return true;
  return permissions.some((p) => p.name === permissionName && p.can_view);
};

/**
 * Возвращает список навигационных секций, отфильтрованных по разрешениям текущего пользователя.
 * Пункты без `key` или с публичным роутом показываются всегда.
 * Секции, у которых все пункты скрыты, тоже скрываются.
 */
export const useFilteredNavLinks = (): readonly NavLinks[] => {
  const permissions = useAppSelector(selectUserPermissions);

  return useMemo(() => {
    return navLinks
      .map((section) => ({
        ...section,
        items: section.items?.filter((item) => isItemVisible(item, permissions)),
      }))
      .filter((section) => (section.items?.length ?? 0) > 0);
  }, [permissions]);
};
