import { useCallback, useMemo, useState } from 'react';

import type { ElementCoordinates } from '@/shared/ui/types';

/** Представляет состояние выбранного элемента. */
interface SelectedItemState<T extends string | number> {
  /** Возвращает идентификатор. */
  readonly id: T;
  /** Возвращает координаты элемента. */
  readonly coordinates: ElementCoordinates;
}

/**
 * Представляет хук всплывающего окна.
 */
export function usePopup<T extends string | number>() {
  const [selectedItem, setSelectedItem] = useState<SelectedItemState<T> | null>(null);

  const handleSelectItem = useCallback((item: SelectedItemState<T> | null) => {
    setSelectedItem(item);
  }, []);

  const handleClose = useCallback(() => {
    setSelectedItem(null);
  }, []);

  return useMemo(
    () => ({ selectedItem, handleSelectItem, handleClose }),
    [handleClose, handleSelectItem, selectedItem],
  );
}
