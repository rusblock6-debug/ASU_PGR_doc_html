import { Combobox } from '@mantine/core';

import { cn } from '@/shared/lib/classnames-utils';
import { ScrollArea } from '@/shared/ui/ScrollArea';
import { TextInput } from '@/shared/ui/TextInput';
import type { SelectOption } from '@/shared/ui/types';

import { useCreatableSelectLogic } from '../../lib/hooks/useCreatableSelectLogic';
import { useDropdownWidth } from '../../lib/hooks/useDropdownWidth';
import { CREATE_OPTION_VALUE } from '../../lib/types';
import { OptionItem } from '../OptionItem';

import styles from './CreatableSelect.module.css';

interface CreatableSelectProps<T extends SelectOption> {
  /** Список опций для выбора. */
  readonly options: readonly T[];
  /** Текущее значение. */
  readonly value?: string | null;
  /** Callback при выборе существующей опции. */
  readonly onChange?: (option: T) => void;
  /** Callback при создании новой записи. Получает введённое название. */
  readonly onCreate?: (label: string) => void;
  /** Callback для переименования опции. */
  readonly onRename?: (value: string, newLabel: string) => Promise<T | void>;
  /**
   * Callback для удаления опции.
   * Получает полную опцию для отображения в диалоге подтверждения.
   * Родитель отвечает за показ подтверждения и выполнение удаления.
   * Возвращает `true` если удаление выполнено, `false` если отменено
   */
  readonly onDelete?: (option: T) => Promise<boolean>;
  /** Callback при потере фокуса. Используется для триггера валидации. */
  readonly onBlur?: () => void;
  /** Callback при очистке значения (когда пользователь удаляет текст и уходит из поля). */
  readonly onClear?: () => void;
  /** Заголовок поля. */
  readonly label?: string;
  /** Текст по умолчанию при отсутствии значения. */
  readonly placeholder?: string;
  /** Отображает звёздочку (*) у заголовка. Только визуальный маркер, не влияет на валидацию. */
  readonly withAsterisk?: boolean;
  /** Только для чтения. */
  readonly readOnly?: boolean;
  /** Заблокировано для взаимодействия. */
  readonly disabled?: boolean;
  /** Ошибка. */
  readonly error?: string;
}

export function CreatableSelect<T extends SelectOption>({
  options,
  value,
  onChange,
  onCreate,
  onRename,
  onDelete,
  onBlur,
  onClear,
  label,
  placeholder = 'Выберите или введите значение',
  withAsterisk,
  readOnly,
  disabled,
  error,
}: CreatableSelectProps<T>) {
  const {
    combobox,
    search,
    filteredOptions,
    editing,
    showCreateOption,
    showOptionMenu,
    rootRef,
    scrollViewportRef,
    handlers,
  } = useCreatableSelectLogic({
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
  });

  // Устанавливаем CSS-переменную --dropdown-width для ограничения текста в опциях
  useDropdownWidth(rootRef);

  const optionElements = filteredOptions.map((option) => (
    <OptionItem
      key={option.value}
      option={option}
      editing={editing}
      showMenu={showOptionMenu}
      showCreateOption={showCreateOption}
      filteredOptions={filteredOptions}
      onOpenMenu={handlers.handleOpenMenu}
      onEditLabelChange={handlers.handleEditLabelChange}
      onFinishEditing={handlers.handleFinishEditing}
      onDelete={handlers.handleDeleteOption}
      onSelectOption={combobox.selectOption}
      hasRename={Boolean(onRename)}
      hasDelete={Boolean(onDelete)}
    />
  ));

  return (
    <div
      ref={rootRef}
      className={styles.root}
    >
      <Combobox
        store={combobox}
        onOptionSubmit={handlers.handleOptionSubmit}
        withinPortal={false}
        offset={2}
        classNames={{
          dropdown: styles.dropdown,
          options: cn(styles.options, { [styles.options_editing]: editing }),
          option: styles.option,
        }}
      >
        <Combobox.Target>
          <TextInput
            classNames={{
              input: cn({ [styles.input_focused]: editing || combobox.dropdownOpened }),
            }}
            label={label}
            withAsterisk={withAsterisk}
            value={search}
            onChange={handlers.handleInputChange}
            onClick={handlers.handleFocus}
            onFocus={handlers.handleFocus}
            onBlur={handlers.handleBlur}
            placeholder={placeholder}
            disabled={disabled}
            readOnly={readOnly}
            error={error}
            withArrow={!readOnly}
            arrowRotated={combobox.dropdownOpened}
          />
        </Combobox.Target>

        <Combobox.Dropdown>
          <Combobox.Options onClick={handlers.handleFinishEditing}>
            <ScrollArea.Autosize
              viewportRef={scrollViewportRef}
              offsetScrollbars="y"
              scrollbars="y"
              type="scroll"
              scrollbarSize={3}
              mah={200}
            >
              {showCreateOption && (
                <Combobox.Option
                  value={CREATE_OPTION_VALUE}
                  className={styles.option_create}
                >
                  Создать «{search.trim()}»
                </Combobox.Option>
              )}

              {optionElements.length > 0
                ? optionElements
                : !showCreateOption && <div className={styles.empty}>Не найдено</div>}
            </ScrollArea.Autosize>
          </Combobox.Options>
        </Combobox.Dropdown>
      </Combobox>
    </div>
  );
}
