import { useEffect, useRef, useState } from 'react';

import { hasValue } from '@/shared/lib/has-value';
import type { SelectOption } from '@/shared/ui/types';

import { filterOptions } from '../filter-options';

interface UseSearchStateProps<T extends SelectOption> {
  /** Список всех опций */
  readonly options: readonly T[];
  /** Текущие название из выбранной опции */
  readonly currentLabel?: string;
  /** Текущее значение для сброса оптимистичного состояния */
  readonly value?: string | null;
  /** Открыт ли дропдаун */
  readonly dropdownOpened: boolean;
}

/**
 * Хук для управления поиском, фильтрацией и оптимистичными обновлениями.
 */
export function useSearchState<T extends SelectOption>({
  options,
  currentLabel,
  value,
  dropdownOpened,
}: UseSearchStateProps<T>) {
  const [optimisticLabel, setOptimisticLabelInternal] = useState<string | null>(null);

  // Ожидаемое название: приоритет у оптимистичного, затем из пропсов
  const expectedLabel = optimisticLabel ?? currentLabel ?? '';

  // Сбрасываем оптимистичное значение, когда приходят обновленные данные
  const prevValueRef = useRef(value);
  useEffect(() => {
    // Сброс при выборе другой опции, но только если опция найдена в списке.
    // Это предотвращает мерцание при создании новой записи,
    // когда value уже установлен, но список ещё не обновился.
    if (prevValueRef.current !== value && hasValue(currentLabel)) {
      setOptimisticLabelInternal(null);
      prevValueRef.current = value;
      return;
    }

    // Сброс когда пришли обновленные данные
    if (optimisticLabel && currentLabel === optimisticLabel) {
      setOptimisticLabelInternal(null);
      prevValueRef.current = value;
    }
  }, [value, currentLabel, optimisticLabel]);

  const [search, setSearchInternal] = useState(expectedLabel);

  // Синхронизируем search с expectedLabel когда дропдаун закрыт
  const prevExpectedLabelRef = useRef(expectedLabel);
  useEffect(() => {
    if (prevExpectedLabelRef.current !== expectedLabel && !dropdownOpened) {
      setSearchInternal(expectedLabel);
    }
    prevExpectedLabelRef.current = expectedLabel;
  }, [expectedLabel, dropdownOpened]);

  // Фильтруем если пользователь изменил search
  // В дальнейшем реализуем callback onSearch для серверного поиска
  const isFiltering = search.toLowerCase().trim() !== expectedLabel.toLowerCase();
  const filteredOptions = isFiltering ? filterOptions(options, search) : options;

  const exactMatch = options.find((option) => option.label.toLowerCase().trim() === search.toLowerCase().trim());

  // Показывать «Создать» — не показываем при точном совпадении или оптимистичном обновлении
  const isOptimisticMatch = optimisticLabel && search.toLowerCase().trim() === optimisticLabel.toLowerCase();
  const showCreateOption = Boolean(search.trim()) && !exactMatch && !isOptimisticMatch;

  const setSearch = (value: string) => {
    setSearchInternal(value);
  };

  const setOptimisticLabel = (label: string | null) => {
    setOptimisticLabelInternal(label);
  };

  return {
    search,
    setSearch,
    setOptimisticLabel,
    expectedLabel,
    filteredOptions,
    exactMatch,
    showCreateOption,
  };
}
