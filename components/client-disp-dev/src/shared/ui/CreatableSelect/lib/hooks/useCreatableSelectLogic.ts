import { useCombobox } from '@mantine/core';
import { type ChangeEvent, useRef } from 'react';

import { hasValueNotEmpty } from '@/shared/lib/has-value';
import { useScrollLock } from '@/shared/lib/hooks/useScrollLock';
import type { SelectOption } from '@/shared/ui/types';

import { CREATE_OPTION_VALUE } from '../types';

import { useAutoSelectCreateOption } from './useAutoSelectCreateOption';
import { useEditingClickOutside } from './useEditingClickOutside';
import { useEditingState } from './useEditingState';
import { useSearchState } from './useSearchState';

interface UseCreatableSelectLogicProps<T extends SelectOption> {
  /** Список опций для выбора. */
  readonly options: readonly T[];
  /** Текущее значение (value выбранной опции). */
  readonly value?: string | null;
  /** Callback при выборе существующей опции. */
  readonly onChange?: (option: T) => void;
  /** Callback при создании новой записи. */
  readonly onCreate?: (label: string) => void;
  /** Callback для переименования опции. */
  readonly onRename?: (value: string, newLabel: string) => Promise<T | void>;
  /** Callback для удаления записи. Возвращает `true` если удаление выполнено, `false` если отменено. */
  readonly onDelete?: (option: T) => Promise<boolean>;
  /** Callback при потере фокуса. */
  readonly onBlur?: () => void;
  /** Callback при очистке значения. */
  readonly onClear?: () => void;
  /** Только для чтения. */
  readonly readOnly?: boolean;
  /** Заблокировано для взаимодействия. */
  readonly disabled?: boolean;
}

/**
 * Хук для управления логикой компонента CreatableSelect.
 *
 * @returns Объект с состоянием и обработчиками:
 * - combobox — Экземпляр useCombobox из Mantine для управления dropdown
 * - search — Текущее значение поискового запроса
 * - filteredOptions — Отфильтрованный список опций по поисковому запросу
 * - editing — Состояние редактирования (текущая редактируемая опция)
 * - showCreateOption — Флаг, показывать ли опцию «Создать…»
 * - showOptionMenu — Флаг, показывать ли меню редактирования опций
 * - rootRef — Ref на корневой элемент для отслеживания кликов вне компонента
 * - scrollViewportRef — Ref на viewport ScrollArea для блокировки скролла
 * - handlers — Объект с обработчиками событий (submit, change, focus, blur и т.д.)
 */
export function useCreatableSelectLogic<T extends SelectOption>({
  options,
  value,
  onChange,
  onCreate,
  onRename,
  onDelete,
  onBlur,
  onClear,
  readOnly,
  disabled,
}: UseCreatableSelectLogicProps<T>) {
  // Находим текущую опцию по value
  const currentOption = options.find((option) => option.value === value);

  // Состояние редактирования
  const { editing, isEditing, startEditing, stopEditing, updateLabel } = useEditingState();

  const combobox = useCombobox({
    // Принудительно держим dropdown открытым во время редактирования
    // undefined вместо false, чтобы не блокировать открытие dropdown
    opened: isEditing ? true : undefined,
    onDropdownClose: () => combobox.resetSelectedOption(),
  });

  // Поиск, фильтрация и оптимистичные обновления
  const { search, setSearch, setOptimisticLabel, expectedLabel, filteredOptions, exactMatch, showCreateOption } =
    useSearchState({
      options,
      currentLabel: currentOption?.label,
      value,
      dropdownOpened: combobox.dropdownOpened,
    });

  // Ref на viewport ScrollArea для блокировки скролла
  const scrollViewportRef = useRef<HTMLDivElement>(null);

  // Блокируем скролл при открытии popover редактирования
  useScrollLock(isEditing, scrollViewportRef);

  // Показывать ли меню редактирования (есть onRename или onDelete)
  const showOptionMenu = Boolean(onRename || onDelete);

  // Выбрать существующую опцию
  const selectOption = (option: T) => {
    setSearch(option.label);
    onChange?.(option);
  };

  // Создать новую запись
  const createNew = (label: string) => {
    const trimmed = label.trim();
    if (hasValueNotEmpty(trimmed)) {
      setSearch(trimmed);
      setOptimisticLabel(trimmed);
      onCreate?.(trimmed);
    }
  };

  // Очистить значение
  const clear = () => {
    setSearch('');
  };

  // Закрыть редактирование
  const closeEditing = () => {
    stopEditing();
    combobox.resetSelectedOption();
  };

  // Завершить редактирование с сохранением изменений
  const handleFinishEditing = async () => {
    if (!editing) return;

    closeEditing();

    if (!onRename) return;

    const trimmedLabel = editing.label.trim();
    const option = options.find((o) => o.value === editing.value);

    if (hasValueNotEmpty(trimmedLabel) && option && trimmedLabel !== option.label.trim()) {
      // Оптимистичное обновление если редактируем текущую выбранную опцию
      if (editing.value === value) {
        setSearch(trimmedLabel);
        setOptimisticLabel(trimmedLabel);
      }

      await onRename(editing.value, trimmedLabel);
    }
  };

  // Ref на root + отслеживание кликов вне dropdown
  const rootRef = useEditingClickOutside(handleFinishEditing);

  // Автоматически выделяем опцию «Создать» при вводе текста без точного совпадения
  useAutoSelectCreateOption(showCreateOption, combobox);

  const handleOptionSubmit = (val: string) => {
    if (val === CREATE_OPTION_VALUE) {
      createNew(search);
    } else {
      const selectedOption = options.find((o) => o.value === val);
      if (selectedOption) {
        selectOption(selectedOption);
      }
    }
    combobox.closeDropdown();
  };

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const newValue = event.currentTarget.value;
    setSearch(newValue);
    combobox.openDropdown();

    if (!hasValueNotEmpty(newValue.trim())) {
      clear();
    }
  };

  const handleFocus = () => {
    if (!readOnly && !disabled) {
      combobox.openDropdown();
    }
  };

  const handleBlur = () => {
    if (isEditing) return;
    combobox.closeDropdown();
    onBlur?.();

    const trimmedSearch = search.trim();

    // Если поле очищено — вызываем onClear
    if (!hasValueNotEmpty(trimmedSearch) && hasValueNotEmpty(value)) {
      onClear?.();
      return;
    }

    if (trimmedSearch === expectedLabel) return;

    if (exactMatch) {
      if (exactMatch.value !== value) {
        selectOption(exactMatch);
      }
      return;
    }

    createNew(trimmedSearch);
  };

  const handleDeleteOption = async (optionValue: string) => {
    if (!onDelete) return;

    const option = options.find((o) => o.value === optionValue);
    if (!option) return;

    const deleted = await onDelete(option);
    if (deleted && optionValue === value) {
      clear();
    }

    closeEditing();
  };

  const handleOpenMenu = (option: SelectOption) => {
    startEditing(option);
  };

  return {
    combobox,
    search,
    filteredOptions,
    editing,
    showCreateOption,
    showOptionMenu,
    rootRef,
    scrollViewportRef,
    handlers: {
      handleOptionSubmit,
      handleInputChange,
      handleFocus,
      handleBlur,
      handleFinishEditing,
      handleDeleteOption,
      handleOpenMenu,
      handleEditLabelChange: updateLabel,
    },
  };
}
