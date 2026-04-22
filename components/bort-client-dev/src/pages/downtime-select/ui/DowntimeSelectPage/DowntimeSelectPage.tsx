import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { ConfirmButton } from '@/widgets/kiosk-controls';

import { useGetOrganizationCategoriesQuery } from '@/shared/api/endpoints/organization-categories';
import { useGetStatusesQuery } from '@/shared/api/endpoints/statuses';
import { useSetVehicleStateTransitionMutation } from '@/shared/api/endpoints/vehicle-state';
import { cn } from '@/shared/lib/classnames-utils';
import { startDowntimeSession } from '@/shared/lib/downtime-session';
import { formatStatusRowLabel } from '@/shared/lib/format-status-row-label';
import { useKioskAside } from '@/shared/lib/kiosk-aside';
import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';
import { getRouteActiveDowntime, getRouteDowntimeSelect, getRouteVehicleStatus } from '@/shared/routes/router';
import { KioskBackButton } from '@/shared/ui/KioskBackButton';

import styles from './DowntimeSelectPage.module.css';

const NEXT_PAGE_ID = '__next_page__';
const PREV_PAGE_ID = '__prev_page__';

/** Базовый элемент выбора (кнопка в сетке). */
interface BaseSelectItem {
  readonly id: string;
  readonly label: string;
}

/** Причина простоя, готовая для отправки в transition. */
interface DowntimeStatusItem extends BaseSelectItem {
  readonly categoryId: string | null;
  /** Только organization_category_id — для сортировки внутри выбранной org-категории */
  readonly organizationCategoryId: string | null;
  /** Код POST /state/transition `new_state` из `system_name` в `/api/statuses`. */
  readonly systemName: string;
}

/** Одна страница 2x4: набор элементов + флаг пагинации вперёд. */
interface PageSlice {
  readonly items: readonly BaseSelectItem[];
  readonly showNext: boolean;
}

/** Слот сетки: элемент, пагинация или пустая ячейка. */
type Slot =
  | { readonly kind: 'item'; readonly item: BaseSelectItem }
  | { readonly kind: 'next' }
  | { readonly kind: 'prev' }
  | { readonly kind: 'empty' };

/** Делит элементы на страницы с резервом ячейки под "следующая страница". */
function buildPageSlices(items: readonly BaseSelectItem[]) {
  const result: PageSlice[] = [];
  let i = 0;
  const n = items.length;
  while (i < n) {
    const remaining = n - i;
    if (remaining > 8) {
      result.push({ items: items.slice(i, i + 7), showNext: true });
      i += 7;
    } else {
      result.push({ items: items.slice(i, n), showNext: false });
      i = n;
    }
  }
  return result;
}

/** Собирает 8 слотов страницы с учетом кнопок "назад/вперёд". */
function buildSlots(page: PageSlice, pageIndex: number) {
  const reservePrev = pageIndex > 0 ? 1 : 0;
  const reserveNext = page.showNext ? 1 : 0;
  const fitsPrevFirst = pageIndex > 0 && reservePrev + page.items.length + reserveNext <= 8;

  if (fitsPrevFirst) {
    const slots: Slot[] = [{ kind: 'prev' }];
    for (const item of page.items) {
      slots.push({ kind: 'item', item });
    }
    if (page.showNext) {
      slots.push({ kind: 'next' });
    }
    while (slots.length < 8) {
      slots.push({ kind: 'empty' });
    }
    return slots.slice(0, 8);
  }

  const slots: Slot[] = page.items.map((item) => ({ kind: 'item', item }) as const);
  if (page.showNext) {
    slots.push({ kind: 'next' });
  }
  while (slots.length < 8) {
    slots.push({ kind: 'empty' });
  }
  const result = slots.slice(0, 8);
  if (pageIndex > 0) {
    const emptyIdx = result.findIndex((s) => s.kind === 'empty');
    if (emptyIdx >= 0) {
      result[emptyIdx] = { kind: 'prev' };
    }
  }
  return result;
}

/** Нормализует подпись категории в kiosk-формат. */
function normalizeCategoryLabel(category: Record<string, unknown>) {
  return formatStatusRowLabel(category);
}

/** Сравнивает идентификаторы как numeric, если возможно. */
function compareDowntimeItemId(a: string, b: string): number {
  const numA = Number(a);
  const numB = Number(b);
  if (Number.isFinite(numA) && Number.isFinite(numB) && String(numA) === a && String(numB) === b) {
    return numA - numB;
  }
  return a.localeCompare(b, undefined, { numeric: true });
}

/** Сортировка по organization_category_id; записи без поля — в конец. */
function compareOrganizationCategoryId(a: string | null, b: string | null): number {
  if (a == null && b == null) {
    return 0;
  }
  if (a == null) {
    return 1;
  }
  if (b == null) {
    return -1;
  }
  return compareDowntimeItemId(a, b);
}

/** Возвращает kiosk-id слота или `null` для пустой ячейки. */
function slotId(slot: Slot) {
  if (slot.kind === 'item') {
    return slot.item.id;
  }
  if (slot.kind === 'next') {
    return NEXT_PAGE_ID;
  }
  if (slot.kind === 'prev') {
    return PREV_PAGE_ID;
  }
  return null;
}

/** Экран выбора простоев: категория -> причина -> переход состояния борта. */
export const DowntimeSelectPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [setTransition, { isLoading: isTransitioning }] = useSetVehicleStateTransitionMutation();
  const { data: statuses = [], isFetching: isStatusesFetching } = useGetStatusesQuery();
  const { data: categories = [], isFetching: isCategoriesFetching } = useGetOrganizationCategoriesQuery();

  const { setAsideLeft } = useKioskAside();
  const { setItemIds, setOnConfirm, selectedId, setSelectedIndex } = useKioskNavigation();

  const [pageIndex, setPageIndex] = useState(0);
  const categoryIdFilter = searchParams.get('categoryId');
  const isCategoryMode = !categoryIdFilter;

  const selectedCategoryDisplayTitle = (() => {
    if (!categoryIdFilter) {
      return null;
    }
    const cat = categories.find((c) => String(c.id) === categoryIdFilter);
    if (!cat) {
      return null;
    }
    return normalizeCategoryLabel(cat as Record<string, unknown>);
  })();

  const downtimeReasons = useMemo<readonly DowntimeStatusItem[]>(
    () =>
      statuses
        .map((status) => {
          const systemRaw = status.system_name;
          if (typeof systemRaw !== 'string' || !systemRaw.trim()) {
            return null;
          }
          const orgCategoryRaw = status.organization_category_id ?? null;
          const categoryIdRaw = orgCategoryRaw ?? status.category_id ?? null;
          return {
            id: String(status.id),
            label: formatStatusRowLabel(status),
            categoryId: categoryIdRaw == null ? null : String(categoryIdRaw),
            organizationCategoryId: orgCategoryRaw == null ? null : String(orgCategoryRaw),
            systemName: systemRaw.trim(),
          };
        })
        .filter((item): item is DowntimeStatusItem => item != null),
    [statuses],
  );

  const downtimeCategories = useMemo<readonly BaseSelectItem[]>(
    () =>
      categories.map((category) => ({
        id: String(category.id),
        label: normalizeCategoryLabel(category as Record<string, unknown>),
      })),
    [categories],
  );

  const filteredDowntimeReasons = useMemo(() => {
    const filtered = downtimeReasons.filter((reason) => reason.categoryId === categoryIdFilter);
    return [...filtered].sort((a, b) => {
      const byOrgCat = compareOrganizationCategoryId(a.organizationCategoryId, b.organizationCategoryId);
      if (byOrgCat !== 0) {
        return byOrgCat;
      }
      return compareDowntimeItemId(a.id, b.id);
    });
  }, [categoryIdFilter, downtimeReasons]);

  const activeItems = isCategoryMode ? downtimeCategories : filteredDowntimeReasons;
  const downtimePages = useMemo(() => buildPageSlices(activeItems), [activeItems]);

  const startDowntime = useCallback(
    (reasonItem: DowntimeStatusItem) => {
      if (isTransitioning || isStatusesFetching) return;
      void setTransition({
        new_state: reasonItem.systemName,
        reason: 'manual',
        comment: reasonItem.label,
      })
        .unwrap()
        .then(() => {
          startDowntimeSession(reasonItem.label);
          void navigate(getRouteActiveDowntime());
        });
    },
    [isStatusesFetching, isTransitioning, setTransition, navigate],
  );

  const selectCategory = useCallback(
    (categoryId: string) => {
      const category = downtimeCategories.find((item) => item.id === categoryId);
      if (!category) {
        return;
      }
      const nextQuery = new URLSearchParams();
      nextQuery.set('categoryId', category.id);
      void navigate({ pathname: getRouteDowntimeSelect(), search: nextQuery.toString() });
    },
    [downtimeCategories, navigate],
  );

  const { slots, slotIds } = useMemo(() => {
    const slice = downtimePages[pageIndex] ?? { items: [] as readonly BaseSelectItem[], showNext: false };
    const s = buildSlots(slice, pageIndex);
    return { slots: s, slotIds: s.map((it) => slotId(it)).filter((id): id is string => id != null) };
  }, [downtimePages, pageIndex]);

  useEffect(() => {
    setPageIndex(0);
  }, [categoryIdFilter]);

  useEffect(() => {
    setPageIndex((p) => Math.min(p, Math.max(0, downtimePages.length - 1)));
  }, [downtimePages.length]);

  useEffect(() => {
    setItemIds(slotIds);
  }, [slotIds, setItemIds]);

  useEffect(() => {
    const handleBack = () => {
      if (isCategoryMode) {
        void navigate(getRouteVehicleStatus());
        return;
      }
      void navigate(getRouteDowntimeSelect());
    };

    setAsideLeft(
      <>
        <KioskBackButton onClick={handleBack} />
        <ConfirmButton disabled={isTransitioning} />
      </>,
    );
    return () => {
      setAsideLeft(null);
    };
  }, [isCategoryMode, setAsideLeft, navigate, isTransitioning]);

  useEffect(() => {
    setOnConfirm(() => {
      if (!selectedId) {
        return;
      }
      if (selectedId === NEXT_PAGE_ID) {
        setPageIndex((p) => Math.min(p + 1, downtimePages.length - 1));
        return;
      }
      if (selectedId === PREV_PAGE_ID) {
        setPageIndex((p) => Math.max(p - 1, 0));
        return;
      }
      if (isCategoryMode) {
        selectCategory(selectedId);
        return;
      }
      const reasonItem = filteredDowntimeReasons.find((r) => r.id === selectedId);
      if (reasonItem) {
        startDowntime(reasonItem);
      }
    });
    return () => {
      setOnConfirm(null);
    };
  }, [
    downtimePages.length,
    filteredDowntimeReasons,
    isCategoryMode,
    selectCategory,
    selectedId,
    setOnConfirm,
    startDowntime,
  ]);

  const isItemDisabled = isCategoryMode ? isCategoriesFetching : isTransitioning || isStatusesFetching;
  const isEmpty = !activeItems.length && (isCategoryMode ? !isCategoriesFetching : !isStatusesFetching);
  let gridAriaLabel = 'Причины простоя';
  if (isCategoryMode) {
    gridAriaLabel = 'Категории простоев';
  } else if (selectedCategoryDisplayTitle) {
    gridAriaLabel = `Причины простоя: ${selectedCategoryDisplayTitle}`;
  }

  return (
    <div className={styles.page}>
      <div
        className={styles.grid}
        role="listbox"
        aria-label={gridAriaLabel}
      >
        {slots.map((slot, index) => {
          const id = slotId(slot);
          const isSelected = id != null && selectedId === id;

          if (slot.kind === 'empty') {
            return (
              <div
                key={`empty-${index}`}
                className={cn(styles.cell, styles.cell_empty)}
                aria-hidden
              />
            );
          }

          if (slot.kind === 'next') {
            return (
              <button
                key={NEXT_PAGE_ID}
                type="button"
                role="option"
                aria-selected={isSelected}
                className={cn(styles.cell, styles.cell_next, isSelected && styles.cell_selected)}
                onClick={() => {
                  setPageIndex((p) => Math.min(p + 1, downtimePages.length - 1));
                }}
              >
                СЛЕДУЮЩАЯ СТРАНИЦА →
              </button>
            );
          }

          if (slot.kind === 'prev') {
            return (
              <button
                key={PREV_PAGE_ID}
                type="button"
                role="option"
                aria-selected={isSelected}
                className={cn(styles.cell, styles.cell_prev, isSelected && styles.cell_selected)}
                onClick={() => {
                  setPageIndex((p) => Math.max(p - 1, 0));
                }}
              >
                ← ПРЕДЫДУЩАЯ СТРАНИЦА
              </button>
            );
          }

          const { item } = slot;
          return (
            <button
              key={`${item.id}-${index}`}
              type="button"
              role="option"
              aria-selected={isSelected}
              disabled={isItemDisabled}
              className={cn(styles.cell, isSelected && styles.cell_selected)}
              onClick={() => {
                const idx = slotIds.indexOf(item.id);
                if (idx >= 0) {
                  setSelectedIndex(idx);
                }
                if (isCategoryMode) {
                  selectCategory(item.id);
                  return;
                }
                const reasonItem = filteredDowntimeReasons.find((reason) => reason.id === item.id);
                if (reasonItem) {
                  startDowntime(reasonItem);
                }
              }}
            >
              {item.label}
            </button>
          );
        })}
        {isEmpty && <div className={styles.empty_state}>Список пуст</div>}
      </div>
    </div>
  );
};
