import { useEffect, useRef, useState } from 'react';

import type { SelectOption } from '@/shared/ui/types';

import { filterOptions } from '../filter-options';

interface UseMultiSearchStateProps<T extends SelectOption> {
  /** Список всех опций */
  readonly options: readonly T[];
  /** Текущие выбранные значения */
  readonly selectedValues: readonly string[];
  /** Скрывать ли уже выбранные опции из списка */
  readonly hidePickedOptions?: boolean;
  /** Открыт ли дропдаун */
  readonly dropdownOpened: boolean;
}

/**
 * Хук для управления поиском и фильтрацией в мульти-селекте.
 */
export function useMultiSearchState<T extends SelectOption>({
  options,
  selectedValues,
  hidePickedOptions,
  dropdownOpened,
}: UseMultiSearchStateProps<T>) {
  const [optimisticLabels, setOptimisticLabelsInternal] = useState<readonly string[]>([]);
  const [search, setSearchInternal] = useState('');

  // Сбрасываем поиск при закрытии дропдауна
  const prevDropdownOpenedRef = useRef(dropdownOpened);
  useEffect(() => {
    if (prevDropdownOpenedRef.current && !dropdownOpened) {
      setSearchInternal('');
    }
    prevDropdownOpenedRef.current = dropdownOpened;
  }, [dropdownOpened]);

  useEffect(() => {
    if (optimisticLabels.length === 0) return;

    const optionLabelsLower = new Set(options.map((o) => o.label.toLowerCase()));
    const stillPending = optimisticLabels.filter((label) => !optionLabelsLower.has(label.toLowerCase()));

    if (stillPending.length !== optimisticLabels.length) {
      setOptimisticLabelsInternal(stillPending);
    }
  }, [options, optimisticLabels]);

  // Фильтруем опции по поиску
  const searchFiltered = filterOptions(options, search);

  // Скрываем уже выбранные опции если нужно
  const selectedValuesSet = new Set(selectedValues);
  const filteredOptions = hidePickedOptions
    ? searchFiltered.filter((item) => !selectedValuesSet.has(item.value))
    : searchFiltered;

  // Опция с точным совпадением названия
  const exactMatch = options.find((option) => option.label.toLowerCase().trim() === search.toLowerCase().trim());

  // Показывать «Создать» — не показываем при точном совпадении или оптимистичном обновлении
  const isOptimisticMatch = optimisticLabels.some(
    (label) => label.toLowerCase().trim() === search.toLowerCase().trim(),
  );
  const showCreateOption = Boolean(search.trim()) && !exactMatch && !isOptimisticMatch;

  const setSearch = (value: string) => {
    setSearchInternal(value);
  };

  const addOptimisticLabel = (label: string) => {
    setOptimisticLabelsInternal((prev) => [...prev, label]);
  };

  const clearSearch = () => {
    setSearchInternal('');
  };

  return {
    search,
    setSearch,
    clearSearch,
    addOptimisticLabel,
    filteredOptions,
    exactMatch,
    showCreateOption,
  };
}
