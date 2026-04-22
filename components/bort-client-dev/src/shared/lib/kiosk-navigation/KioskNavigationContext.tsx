import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';

/**
 * Контракт контекста фокусной навигации и confirm для kiosk UI (кнопка «назад» — в KioskLeftSidebar).
 */
export interface KioskNavigationContextValue {
  readonly itemIds: readonly string[];
  readonly selectedIndex: number;
  readonly selectedId: string | null;
  readonly setItemIds: (ids: readonly string[]) => void;
  readonly setSelectedIndex: (index: number) => void;
  readonly moveUp: () => void;
  readonly moveDown: () => void;
  readonly setOnConfirm: (handler: (() => void) | null) => void;
  readonly confirm: () => void;
}

const KioskNavigationContext = createContext<KioskNavigationContextValue | null>(null);

/**
 * Пропсы провайдера kiosk-навигации.
 */
interface KioskNavigationProviderProps {
  readonly children: ReactNode;
}

/**
 * Провайдер фокуса списка и подтверждения для kiosk UI.
 */
export const KioskNavigationProvider = ({ children }: KioskNavigationProviderProps) => {
  const [itemIds, setItemIdsState] = useState<string[]>([]);
  const [selectedIndex, setSelectedIndexState] = useState(0);
  const itemIdsRef = useRef<string[]>([]);
  const onConfirmRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    itemIdsRef.current = itemIds;
  }, [itemIds]);

  const setItemIds = useCallback((ids: readonly string[]) => {
    const next = [...ids];
    setItemIdsState(next);
    itemIdsRef.current = next;
    setSelectedIndexState(0);
  }, []);

  const setSelectedIndex = useCallback((index: number) => {
    setSelectedIndexState((prev) => {
      const len = itemIdsRef.current.length;
      if (len === 0) {
        return 0;
      }
      const clamped = Math.max(0, Math.min(len - 1, index));
      return Number.isFinite(clamped) ? clamped : prev;
    });
  }, []);

  const moveUp = useCallback(() => {
    setSelectedIndexState((i) => Math.max(0, i - 1));
  }, []);

  const moveDown = useCallback(() => {
    setSelectedIndexState((i) => {
      const len = itemIdsRef.current.length;
      if (len === 0) {
        return 0;
      }
      return Math.min(len - 1, i + 1);
    });
  }, []);

  const selectedId = itemIds.length > 0 ? (itemIds[selectedIndex] ?? null) : null;

  const setOnConfirm = useCallback((handler: (() => void) | null) => {
    onConfirmRef.current = handler;
  }, []);

  const confirm = useCallback(() => {
    onConfirmRef.current?.();
  }, []);

  const value: KioskNavigationContextValue = useMemo(
    () => ({
      itemIds,
      selectedIndex,
      selectedId,
      setItemIds,
      setSelectedIndex,
      moveUp,
      moveDown,
      setOnConfirm,
      confirm,
    }),
    [itemIds, selectedIndex, selectedId, setItemIds, setSelectedIndex, moveUp, moveDown, setOnConfirm, confirm],
  );

  return <KioskNavigationContext.Provider value={value}>{children}</KioskNavigationContext.Provider>;
};

/**
 * Доступ к состоянию kiosk-навигации; только внутри KioskNavigationProvider.
 */
export const useKioskNavigation = () => {
  const ctx = useContext(KioskNavigationContext);
  if (!ctx) {
    throw new Error('useKioskNavigation must be used within KioskNavigationProvider');
  }
  return ctx;
};
