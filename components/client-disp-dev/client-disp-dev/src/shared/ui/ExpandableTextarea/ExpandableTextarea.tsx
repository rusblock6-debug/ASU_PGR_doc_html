import { type TextInputProps as MantineTextInputProps } from '@mantine/core';
import { type ChangeEvent, type ReactNode, useEffect, useRef, useState } from 'react';

import { cn } from '@/shared/lib/classnames-utils';
import { hasValue } from '@/shared/lib/has-value';
import { mergeMantineClassNames } from '@/shared/lib/merge-mantine-classnames';
import { mantineInput, mantineInputWrapper } from '@/shared/styles/mantine';
import { Popover, PopoverDropdown, PopoverTarget } from '@/shared/ui/Popover';
import { Textarea } from '@/shared/ui/Textarea';
import { TextInput } from '@/shared/ui/TextInput';
import type { BaseInputOption } from '@/shared/ui/types';

import styles from './ExpandableTextarea.module.css';

/**
 * Представляет свойства для компонента расширяемого текстового ввода со счетчиком введенных символов.
 */
interface ExpandableTextareaProps extends BaseInputOption {
  /** Текущее значение. */
  readonly value: string;
  /** Вызывается при изменении текста. */
  readonly onChange: (value: string) => void;
  /** Максимальное количество символов (для счётчика). */
  readonly maxLength?: number;
  /** Максимальное количество строк при раскрытии. */
  readonly maxRows?: number;
  /** Текст по умолчанию при отсутствии значения. */
  readonly placeholder?: string;
  /** Заблокировано для взаимодействия. */
  readonly disabled?: boolean;
  /** Сообщение об ошибке. */
  readonly error?: ReactNode;
  /** Заголовок поля. */
  readonly label?: ReactNode;
  /** Обязательное поле. */
  readonly required?: boolean;
  /** Дополнительный CSS-класс. */
  readonly className?: string;
  /** Объект с классами для кастомизации внутренних элементов компонента. */
  readonly classNames?: MantineTextInputProps['classNames'];
}

/**
 * Компонент расширяемого текстового ввода.
 * В свёрнутом состоянии выглядит как текстовое поле с обрезанным текстом.
 * При клике разворачивается в плавающую текстовую область и счётчиком символов.
 */
export function ExpandableTextarea({
  value,
  onChange,
  maxLength,
  maxRows = 10,
  placeholder = 'Не указан',
  disabled = false,
  error,
  label,
  required,
  className,
  classNames,
  inputSize = 'combobox-sm',
  variant = 'combobox-primary',
  labelPosition = 'vertical',
}: Readonly<ExpandableTextareaProps>) {
  const [opened, setOpened] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const triggerRef = useRef<HTMLInputElement>(null);

  const [triggerHeight, setTriggerHeight] = useState(0);

  const [localValue, setLocalValue] = useState(value);
  const isUserInputRef = useRef(false);

  useEffect(() => {
    if (!isUserInputRef.current) {
      setLocalValue(value);
    }
    isUserInputRef.current = false;
  }, [value]);

  useEffect(() => {
    if (triggerRef.current) {
      setTriggerHeight(triggerRef.current.offsetHeight);
    }
  }, [opened]);

  const handleOpen = () => {
    if (disabled) return;
    setOpened(true);
    setTimeout(() => {
      textareaRef.current?.focus();
      const length = textareaRef.current?.value.length ?? 0;
      textareaRef.current?.setSelectionRange(length, length);
    }, 0);
  };

  const handleClose = () => {
    setOpened(false);
  };

  const handleChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = event.currentTarget.value;
    if (maxLength && newValue.length > maxLength) {
      return;
    }
    isUserInputRef.current = true;
    setLocalValue(newValue);
    onChange(newValue);
  };

  const classNamesObj = typeof classNames === 'object' ? classNames : null;
  const inputClassNames = mergeMantineClassNames(mantineInput, classNamesObj);

  return (
    <Popover
      opened={opened}
      onChange={setOpened}
      position="bottom-start"
      width="target"
      trapFocus={false}
      closeOnClickOutside
      offset={{ mainAxis: -triggerHeight }}
    >
      <PopoverTarget>
        <TextInput
          ref={triggerRef}
          value={localValue}
          readOnly
          onClick={handleOpen}
          onFocus={handleOpen}
          placeholder={placeholder}
          disabled={disabled}
          error={error}
          label={label}
          required={required}
          className={cn(styles.trigger, className)}
          classNames={mergeMantineClassNames(
            mantineInput,
            mantineInputWrapper,
            {
              input: cn({ [styles.active]: opened }),
            },
            classNamesObj,
          )}
          inputSize={inputSize}
          variant={variant}
          mod={{ 'input-size': inputSize, 'label-position': labelPosition }}
          labelPosition={labelPosition}
        />
      </PopoverTarget>

      <PopoverDropdown className={styles.dropdown}>
        <div
          className={cn(styles.textarea_wrapper, inputClassNames?.input, { [styles.active]: opened })}
          data-variant={variant}
        >
          <Textarea
            ref={textareaRef}
            value={localValue}
            onChange={handleChange}
            onBlur={handleClose}
            placeholder={placeholder}
            autosize
            minRows={1}
            maxRows={maxRows}
            inputSize={inputSize}
            variant={variant}
            classNames={{ input: styles.input }}
            labelPosition={labelPosition}
          />
          {hasValue(maxLength) && (
            <div className={styles.char_counter}>
              {localValue.length}/{maxLength}
            </div>
          )}
        </div>
      </PopoverDropdown>
    </Popover>
  );
}
