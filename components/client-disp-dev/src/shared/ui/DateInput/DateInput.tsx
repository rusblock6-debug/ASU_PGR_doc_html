import 'dayjs/locale/ru';
import {
  DateInput as MantineDateInput,
  type DateInputProps as MantineDateInputProps,
  DatesProvider,
} from '@mantine/dates';

import { Z_INDEX } from '@/shared/lib/constants';
import { getCalendarDayProps } from '@/shared/lib/mantine/get-calendar-day-props';
import { mergeMantineClassNames } from '@/shared/lib/merge-mantine-classnames';
import { mantineInput, mantineInputWrapper } from '@/shared/styles/mantine';
import type { BaseInputOption } from '@/shared/ui/types';

/**
 * Представляет свойства для компонента выбора даты.
 */
interface DatePickerProps
  extends Omit<MantineDateInputProps, 'valueFormat' | 'clearable' | 'variant' | 'inputSize'>, BaseInputOption {
  /**
   * Возвращает локаль.
   */
  readonly locale?: string;
  /**
   * Возвращает формат даты.
   */
  readonly valueFormat?: string;
  /**
   * Возвращает признак доступности очистки поля ввода.
   */
  readonly clearable?: boolean;
  /**
   * Возвращает значение zIndex.
   */
  readonly zIndex?: number;
}

/**
 * Представляет компонент поля ввода для выбора даты.
 */
export function DateInput({
  locale = 'ru',
  valueFormat = 'DD.MM.YYYY',
  clearable = true,
  zIndex = Z_INDEX.MODAL,
  inputSize = 'xs',
  variant = 'default',
  placeholder = 'Не указан',
  labelPosition = 'horizontal',
  popoverProps,
  classNames,
  ...props
}: DatePickerProps) {
  const classNamesObj = typeof classNames === 'object' ? classNames : undefined;

  return (
    <DatesProvider settings={{ locale }}>
      <MantineDateInput
        {...props}
        mod={{ 'input-size': inputSize, 'label-position': labelPosition }}
        valueFormat={valueFormat}
        clearable={clearable}
        variant={variant}
        placeholder={placeholder}
        classNames={mergeMantineClassNames(mantineInput, mantineInputWrapper, {
          ...classNamesObj,
        })}
        popoverProps={{
          ...popoverProps,
          zIndex,
        }}
        getDayProps={getCalendarDayProps}
      />
    </DatesProvider>
  );
}
