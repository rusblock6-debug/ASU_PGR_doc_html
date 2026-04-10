import { useCombobox } from '@mantine/core';
import { type ChangeEvent, useRef } from 'react';

import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue, hasValueNotEmpty } from '@/shared/lib/has-value';
import { useScrollLock } from '@/shared/lib/hooks/useScrollLock';
import type { SelectOption } from '@/shared/ui/types';

import { CREATE_OPTION_VALUE } from '../types';

import { useAutoSelectCreateOption } from './useAutoSelectCreateOption';
import { useEditingClickOutside } from './useEditingClickOutside';
import { useEditingState } from './useEditingState';
import { useMultiSearchState } from './useMultiSearchState';

interface UseMultiSelectLogicProps<T extends SelectOption> {
  /** Список опций для выбора. */
  readonly options: readonly T[];
  /** Текущие выбранные значения. */
  readonly value?: readonly string[];
  /** Callback при изменении выбранных опций. */
  readonly onChange?: (options: readonly T[]) => void;
  /** Callback при создании новой записи. */
  readonly onCreate?: (label: string) => void;
  /** Callback для переименования опции. */
  readonly onRename?: (value: string, newLabel: string) => Promise<T | void>;
  /** Callback для удаления записи. Возвращает `true` если удаление выполнено, `false` если отменено. */
  readonly onDelete?: (option: T) => Promise<boolean>;
  /** Callback при потере фокуса. Используется для триггера валидации. */
  readonly onBlur?: () => void;
  /** Callback при полной очистке выбранных значений. */
  readonly onClear?: () => void;
  /** Максимальное количество выбранных значений. */
  readonly maxValues?: number;
  /** Скрывать ли уже выбранные опции из списка. */
  readonly hidePickedOptions?: boolean;
  /** Только для чтения. */
  readonly readOnly?: boolean;
  /** Заблокировано для взаимодействия. */
  readonly disabled?: boolean;
}

/**
 * Хук для управления логикой компонента CreatableMultiSelect.
 *
 * @returns Объект с состоянием и обработчиками:
 * - combobox — Экземпляр useCombobox из Mantine для управления dropdown
 * - search — Текущее значение поискового запроса
 * - selectedOptions — Массив выбранных опций
 * - filteredOptions — Отфильтрованный список опций по поисковому запросу
 * - editing — Состояние редактирования (текущая редактируемая опция)
 * - showCreateOption — Флаг, показывать ли опцию «Создать…»
 * - showOptionMenu — Флаг, показывать ли меню редактирования опций
 * - isMaxReached — Флаг достижения максимального количества выбранных значений
 * - rootRef — Ref на корневой элемент для отслеживания кликов вне компонента
 * - scrollViewportRef — Ref на viewport ScrollArea для блокировки скролла
 * - handlers — Объект с обработчиками событий (submit, change, focus, blur, remove и т.д.)
 */
export function useMultiSelectLogic<T extends SelectOption>({
  options,
  value = EMPTY_ARRAY,
  onChange,
  onCreate,
  onRename,
  onDelete,
  onBlur,
  onClear,
  maxValues,
  hidePickedOptions,
  readOnly,
  disabled,
}: UseMultiSelectLogicProps<T>) {
  const selectedOptions = valuesToOptions(value, options);

  const { editing, isEditing, startEditing, stopEditing, updateLabel } = useEditingState();

  // Защита от двойного сабмита и создания в handleBlur.
  // Enter вызывает handleOptionSubmit дважды (onClick + onKeyDown).
  // После сабмита срабатывает handleBlur, который тоже может создать запись.
  // Запоминаем время последнего сабмита и игнорируем повторы в течение 100ms
  const lastSubmitTimeRef = useRef(0);

  const combobox = useCombobox({
    // Принудительно держим dropdown открытым во время редактирования
    // undefined вместо false, чтобы не блокировать открытие dropdown
    opened: isEditing ? true : undefined,
    onDropdownClose: () => combobox.resetSelectedOption(),
  });

  const { search, setSearch, clearSearch, addOptimisticLabel, filteredOptions, exactMatch, showCreateOption } =
    useMultiSearchState({
      options,
      selectedValues: value,
      hidePickedOptions,
      dropdownOpened: combobox.dropdownOpened,
    });

  // Ref на viewport ScrollArea для блокировки скролла
  const scrollViewportRef = useRef<HTMLDivElement>(null);

  // Блокируем скролл при открытии popover редактирования
  useScrollLock(isEditing, scrollViewportRef);

  // Показывать ли меню редактирования (есть onRename или onDelete)
  const showOptionMenu = Boolean(onRename || onDelete);

  // Проверка достижения лимита
  const isMaxReached = hasValue(maxValues) && value.length >= maxValues;

  // Добавить опцию к выбранным
  const addOption = (option: T) => {
    if (isMaxReached) return;
    if (value.includes(option.value)) return;

    const newValues = [...value, option.value];
    const newOptions = valuesToOptions(newValues, options);

    if (!newOptions.find((o) => o.value === option.value)) {
      newOptions.push(option);
    }

    onChange?.(newOptions);
  };

  // Удалить опцию из выбранных
  const removeOption = (optionValue: string) => {
    const newValues = value.filter((v) => v !== optionValue);
    const newOptions = valuesToOptions(newValues, options);
    onChange?.(newOptions);
  };

  // Создать новую запись
  const createNew = (label: string) => {
    if (isMaxReached) return;

    const trimmed = label.trim();
    if (hasValueNotEmpty(trimmed)) {
      addOptimisticLabel(trimmed);
      onCreate?.(trimmed);
    }
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
      await onRename(editing.value, trimmedLabel);
    }
  };

  // Ref на root + отслеживание кликов вне dropdown
  const rootRef = useEditingClickOutside(handleFinishEditing);

  // Автоматически выделяем опцию «Создать» при вводе текста без точного совпадения
  useAutoSelectCreateOption(showCreateOption, combobox);

  const handleOptionSubmit = (val: string) => {
    const now = Date.now();

    // Защита от двойного вызов — игнорируем повторные вызовы в течение 100ms
    if (now - lastSubmitTimeRef.current < 100) {
      return;
    }

    lastSubmitTimeRef.current = now;

    if (val === CREATE_OPTION_VALUE) {
      createNew(search);
      clearSearch();
    } else {
      const selectedOption = options.find((o) => o.value === val);
      if (selectedOption) {
        if (value.includes(selectedOption.value)) {
          removeOption(selectedOption.value);
        } else {
          addOption(selectedOption);
        }
        clearSearch();
      }
    }
  };

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const newValue = event.currentTarget.value;
    setSearch(newValue);
    combobox.openDropdown();
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

    // Если только что был сабмит (< 100ms назад), не создаем дубликат
    if (Date.now() - lastSubmitTimeRef.current < 100) {
      return;
    }

    // При потере фокуса создаем новую запись если введен текст и нет точного совпадения
    const trimmedSearch = search.trim();
    if (trimmedSearch && !exactMatch) {
      createNew(trimmedSearch);
    }

    clearSearch();
  };

  const handleDeleteOption = async (optionValue: string) => {
    if (!onDelete) return;

    const option = options.find((o) => o.value === optionValue);
    if (!option) return;

    const deleted = await onDelete(option);
    if (deleted && value.includes(optionValue)) {
      removeOption(optionValue);
    }

    closeEditing();
  };

  const handleOpenMenu = (option: SelectOption) => {
    startEditing(option);
  };

  const handleRemovePill = (optionValue: string) => {
    removeOption(optionValue);

    // Если удалили последний элемент — вызываем onClear
    if (value.length === 1 && value[0] === optionValue) {
      onClear?.();
    }
  };

  return {
    combobox,
    search,
    selectedOptions,
    filteredOptions,
    editing,
    showCreateOption,
    showOptionMenu,
    isMaxReached,
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
      handleRemovePill,
      handleEditLabelChange: updateLabel,
    },
  };
}

/**
 * Преобразует массив значений в массив соответствующих опций.
 * Фильтрует несуществующие опции.
 *
 * @example
 * ```ts
 * const options = [
 *   { value: '1', label: 'Frontend' },
 *   { value: '2', label: 'Backend' },
 * ];
 * const values = ['1', '2', '3']; // '3' не существует в options
 * const result = valuesToOptions(values, options);
 * // result: [{ value: '1', label: 'Frontend' }, { value: '2', label: 'Backend' }]
 * ```
 */
function valuesToOptions<T extends SelectOption>(values: readonly string[], options: readonly T[]) {
  return values
    .map((value) => {
      return options.find((option) => option.value === value);
    })
    .filter(hasValue);
}
