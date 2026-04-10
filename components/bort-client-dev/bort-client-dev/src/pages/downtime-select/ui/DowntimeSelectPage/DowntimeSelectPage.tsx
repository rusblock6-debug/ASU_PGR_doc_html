import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { ConfirmButton } from '@/widgets/kiosk-controls';

import { useSetVehicleStateTransitionMutation } from '@/shared/api';
import { cn } from '@/shared/lib/classnames-utils';
import { startDowntimeSession } from '@/shared/lib/downtime-session';
import { useKioskAside } from '@/shared/lib/kiosk-aside';
import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';
import { getRouteActiveDowntime, getRouteVehicleStatus } from '@/shared/routes/router';
import { KioskBackButton } from '@/shared/ui/KioskBackButton';

import type { DowntimeReasonItem } from '../../lib/downtime-reasons';
import { DOWNTIME_REASONS } from '../../lib/downtime-reasons';

import styles from './DowntimeSelectPage.module.css';

const NEXT_PAGE_ID = '__next_page__';
const PREV_PAGE_ID = '__prev_page__';

/** Фрагмент списка причин для одной страницы сетки и флаг «есть ещё». */
interface PageSlice {
  readonly items: readonly DowntimeReasonItem[];
  readonly showNext: boolean;
}

/** Разбиение списка на страницы: при >8 оставшихся — 7 элементов + слот «след. страница». */
function buildPageSlices(items: readonly DowntimeReasonItem[]): PageSlice[] {
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

/** Слот ячейки 2×4: причина, навигация по страницам или пусто. */
type Slot =
  | { readonly kind: 'item'; readonly item: DowntimeReasonItem }
  | { readonly kind: 'next' }
  | { readonly kind: 'prev' }
  | { readonly kind: 'empty' };

/**
 * До 8 слотов сетки 2×4. На страницах после первой — «пред.» в начале, если помещается;
 * иначе «пред.» в первой свободной ячейке (страница 7+«далее»).
 */
function buildSlots(page: PageSlice, pageIndex: number): Slot[] {
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

const DOWNTIME_PAGES = buildPageSlices(DOWNTIME_REASONS);

/** Идентификатор для kiosk-навигации (пустые слоты без id). */
function slotId(slot: Slot): string | null {
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

/**
 * Выбор причины простоя из фиксированного списка; подтверждение → POST /state/transition.
 */
export const DowntimeSelectPage = () => {
  const navigate = useNavigate();
  const [setTransition, { isLoading: isTransitioning }] = useSetVehicleStateTransitionMutation();

  const { setAsideLeft } = useKioskAside();
  const { setItemIds, setOnConfirm, selectedId, setSelectedIndex } = useKioskNavigation();

  const [pageIndex, setPageIndex] = useState(0);

  const { slots, slotIds } = useMemo(() => {
    const slice = DOWNTIME_PAGES[pageIndex] ?? { items: [] as readonly DowntimeReasonItem[], showNext: false };
    const s = buildSlots(slice, pageIndex);
    return { slots: s, slotIds: s.map((it) => slotId(it)).filter((id): id is string => id != null) };
  }, [pageIndex]);

  useEffect(() => {
    setPageIndex((p) => Math.min(p, Math.max(0, DOWNTIME_PAGES.length - 1)));
  }, []);

  useEffect(() => {
    setItemIds(slotIds);
  }, [slotIds, setItemIds]);

  useEffect(() => {
    setAsideLeft(
      <>
        <KioskBackButton onClick={() => void navigate(getRouteVehicleStatus())} />
        <ConfirmButton disabled={isTransitioning} />
      </>,
    );
    return () => {
      setAsideLeft(null);
    };
  }, [setAsideLeft, navigate, isTransitioning]);

  useEffect(() => {
    setOnConfirm(() => {
      if (!selectedId) {
        return;
      }
      if (selectedId === NEXT_PAGE_ID) {
        setPageIndex((p) => Math.min(p + 1, DOWNTIME_PAGES.length - 1));
        return;
      }
      if (selectedId === PREV_PAGE_ID) {
        setPageIndex((p) => Math.max(p - 1, 0));
        return;
      }
      const reasonItem = DOWNTIME_REASONS.find((r) => r.id === selectedId);
      if (!reasonItem) {
        return;
      }
      void setTransition({ new_state: 'idle', reason: 'manual', comment: reasonItem.label })
        .unwrap()
        .then(() => {
          startDowntimeSession(reasonItem.label);
          void navigate(getRouteActiveDowntime());
        });
    });
    return () => {
      setOnConfirm(null);
    };
  }, [selectedId, setOnConfirm, setTransition, navigate]);

  return (
    <div className={styles.page}>
      <div
        className={styles.grid}
        role="listbox"
        aria-label="Причины простоя"
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
                  setPageIndex((p) => Math.min(p + 1, DOWNTIME_PAGES.length - 1));
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
              className={cn(styles.cell, isSelected && styles.cell_selected)}
              onClick={() => {
                const idx = slotIds.indexOf(item.id);
                if (idx >= 0) {
                  setSelectedIndex(idx);
                }
              }}
            >
              {item.label}
            </button>
          );
        })}
      </div>
    </div>
  );
};
