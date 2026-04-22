import { Combobox, Pill, PillsInput } from '@mantine/core';

import ArrowDownIcon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { hasValue } from '@/shared/lib/has-value';
import { mergeMantineClassNames } from '@/shared/lib/merge-mantine-classnames';
import { mantineInput, mantineInputWrapper } from '@/shared/styles/mantine';
import { ScrollArea } from '@/shared/ui/ScrollArea';
import type { SelectOption } from '@/shared/ui/types';

import { useDropdownWidth } from '../../lib/hooks/useDropdownWidth';
import { useMultiSelectLogic } from '../../lib/hooks/useMultiSelectLogic';
import { CREATE_OPTION_VALUE } from '../../lib/types';
import styles from '../CreatableSelect/CreatableSelect.module.css';
import { OptionItem } from '../OptionItem';
import { PillItem } from '../PillItem';

import cls from './CreatableMultiSelect.module.css';

/** Свойства компонента для множественного выбора опций с возможностью создания новых записей, редактирования и удаления. */
interface CreatableMultiSelectProps<T extends SelectOption> {
  /** Список опций для выбора. */
  readonly options: readonly T[];
  /** Текущие выбранные значения. */
  readonly value?: string[];
  /** Callback при изменении выбранных опций. */
  readonly onChange?: (options: readonly T[]) => void;
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
  /** Callback при полной очистке выбранных значений. */
  readonly onClear?: () => void;
  /** Максимальное количество выбранных значений. */
  readonly maxValues?: number;
  /** Скрывать уже выбранные опции из списка. */
  readonly hidePickedOptions?: boolean;
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

/** Компонент для множественного выбора опций с возможностью создания новых записей, редактирования и удаления. */
export function CreatableMultiSelect<T extends SelectOption>({
  options,
  value,
  onChange,
  onCreate,
  onRename,
  onDelete,
  onBlur,
  onClear,
  maxValues,
  hidePickedOptions,
  label,
  placeholder = 'Выберите или введите значение',
  withAsterisk,
  readOnly,
  disabled,
  error,
}: CreatableMultiSelectProps<T>) {
  const {
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
    handlers,
  } = useMultiSelectLogic({
    options,
    value,
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
        <Combobox.Target withKeyboardNavigation={false}>
          <PillsInput
            mod={{ 'input-size': 'xs', 'label-position': 'horizontal' }}
            variant="default"
            className={cn(cls.pills_input, { [cls.without_label]: !hasValue(label) })}
            classNames={mergeMantineClassNames(mantineInput, mantineInputWrapper, {
              input: cn(cls.input_multi_wrapper, { [styles.input_focused]: editing || combobox.dropdownOpened }),
              section: cls.input_multi_arrow_section,
            })}
            label={label}
            withAsterisk={withAsterisk}
            onClick={handlers.handleClick}
            disabled={disabled}
            error={error}
            rightSection={
              <div className={cls.arrow_icon}>
                <ArrowDownIcon className={cn(cls.arrow, { [cls.arrow_rotated]: combobox.dropdownOpened })} />
              </div>
            }
            rightSectionWidth={32}
            rightSectionPointerEvents="none"
          >
            <Pill.Group className={cls.pill_group}>
              {selectedOptions.map((option) => (
                <PillItem
                  key={option.value}
                  option={option}
                  onRemove={handlers.handleRemovePill}
                  disabled={disabled}
                  readOnly={readOnly}
                />
              ))}

              <Combobox.EventsTarget>
                <PillsInput.Field
                  data-pills-input="true"
                  className={cls.input_field}
                  value={search}
                  onChange={handlers.handleInputChange}
                  onBlur={handlers.handleBlur}
                  placeholder={selectedOptions.length === 0 ? placeholder : ''}
                  disabled={disabled || isMaxReached}
                  readOnly={readOnly}
                />
              </Combobox.EventsTarget>
            </Pill.Group>
          </PillsInput>
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
              {showCreateOption && !isMaxReached && onCreate && (
                <Combobox.Option
                  value={CREATE_OPTION_VALUE}
                  className={styles.option_create}
                >
                  Создать «{search.trim()}»
                </Combobox.Option>
              )}

              {optionElements.length > 0 ? optionElements : !onCreate && <div className={styles.empty}>Не найдено</div>}
            </ScrollArea.Autosize>
          </Combobox.Options>
        </Combobox.Dropdown>
      </Combobox>
    </div>
  );
}
