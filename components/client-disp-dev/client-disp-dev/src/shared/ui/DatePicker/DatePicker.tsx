import { DatePicker as MantineDatePicker, type DatePickerProps, DatesProvider } from '@mantine/dates';

import { getCalendarDayProps } from '@/shared/lib/mantine/get-calendar-day-props';

/**
 * Представляет компонент календаря для выбора даты.
 */
export function DatePicker({ locale = 'ru', ...props }: Readonly<DatePickerProps>) {
  return (
    <DatesProvider settings={{ locale }}>
      <MantineDatePicker
        {...props}
        getDayProps={getCalendarDayProps}
      />
    </DatesProvider>
  );
}

type RangeDatePickerProps = Omit<DatePickerProps<'range'>, 'type'>;

/**
 * Представляет компонент календаря для выбора диапазона дат.
 */
export function RangeDatePicker({ locale = 'ru', ...props }: Readonly<RangeDatePickerProps>) {
  return (
    <DatesProvider settings={{ locale }}>
      <MantineDatePicker
        type="range"
        {...props}
        getDayProps={getCalendarDayProps}
      />
    </DatesProvider>
  );
}
