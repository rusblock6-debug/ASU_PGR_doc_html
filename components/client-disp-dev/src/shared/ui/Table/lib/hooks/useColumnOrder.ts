import type { DragEndEvent } from '@dnd-kit/core';
import { arrayMove } from '@dnd-kit/sortable';
import { useCallback, useEffect, useState } from 'react';

/**
 * Хук для управления порядком колонок с поддержкой DnD и LocalStorage
 */
export function useColumnOrder(initialColumnIds: string[], storageKey?: string) {
  // Инициализация порядка колонок из LocalStorage или defaults
  const [columnOrder, setColumnOrder] = useState<string[]>(() => {
    if (!storageKey) {
      return initialColumnIds;
    }

    const stored = localStorage.getItem(`${storageKey}-column-order`);
    if (stored) {
      const parsed = JSON.parse(stored) as string[];
      // Проверяем, что все колонки из initialColumnIds есть в сохраненном порядке
      if (parsed.length === initialColumnIds.length && initialColumnIds.every((id) => parsed.includes(id))) {
        return parsed;
      }
    }

    return initialColumnIds;
  });

  // Сохранение порядка колонок в LocalStorage при изменении
  useEffect(() => {
    if (!storageKey) return;

    localStorage.setItem(`${storageKey}-column-order`, JSON.stringify(columnOrder));
  }, [columnOrder, storageKey]);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;

    if (!over || active.id === over.id) {
      return;
    }

    // Не перемещаем колонки 'select' и 'dummyColumn'
    if (active.id === 'select' || over.id === 'select' || active.id === 'dummyColumn' || over.id === 'dummyColumn') {
      return;
    }

    setColumnOrder((prevOrder) => {
      const oldIndex = prevOrder.indexOf(active.id as string);
      const newIndex = prevOrder.indexOf(over.id as string);

      if (oldIndex === -1 || newIndex === -1) {
        return prevOrder;
      }

      // Находим индекс колонки dummyColumn
      const dummyColumnIndex = prevOrder.indexOf('dummyColumn');

      // Если пытаемся переместить колонку за dummyColumn, запрещаем
      if (dummyColumnIndex !== -1 && newIndex >= dummyColumnIndex) {
        return prevOrder;
      }

      return arrayMove(prevOrder, oldIndex, newIndex);
    });
  }, []);

  return {
    columnOrder,
    setColumnOrder,
    handleDragEnd,
  };
}
