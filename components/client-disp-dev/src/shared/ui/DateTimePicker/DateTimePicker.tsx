import 'dayjs/locale/ru';
import {
  DatesProvider,
  DateTimePicker as MantineDateTimePicker,
  type DateTimePickerProps as MantineDateTimePickerProps,
} from '@mantine/dates';

import { Z_INDEX } from '@/shared/lib/constants';
import { getCalendarDayProps } from '@/shared/lib/mantine/get-calendar-day-props';
import { mergeMantineClassNames } from '@/shared/lib/merge-mantine-classnames';
import { mantineInput, mantineInputWrapper } from '@/shared/styles/mantine';
import type { BaseInputOption } from '@/shared/ui/types';

interface DateTimePickerProps
  extends Omit<MantineDateTimePickerProps, 'valueFormat' | 'clearable' | 'variant' | 'inputSize'>, BaseInputOption {
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
 * Представляет компонент выбора даты с временем.
 */
export function DateTimePicker({
  locale = 'ru',
  valueFormat = 'DD.MM.YYYY HH:mm:ss',
  clearable = true,
  zIndex = Z_INDEX.MODAL,
  inputSize = 'xs',
  variant = 'default',
  placeholder = 'Не указан',
  labelPosition = 'horizontal',
  popoverProps,
  classNames,
  ...props
}: DateTimePickerProps) {
  const classNamesObj = typeof classNames === 'object' ? classNames : undefined;

  return (
    <DatesProvider settings={{ locale }}>
      <MantineDateTimePicker
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
        withSeconds
        getDayProps={getCalendarDayProps}
      />
    </DatesProvider>
  );
}
