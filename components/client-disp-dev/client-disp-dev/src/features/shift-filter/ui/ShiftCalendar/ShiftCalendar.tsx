import type { DatesRangeValue } from '@mantine/dates';
import { format } from 'date-fns';
import { type ChangeEvent, useState } from 'react';

import { END_SHIFT_OFFSET, getShiftByDate, getShiftsByDate, type ShiftInfo } from '@/entities/shift';

import type { ShiftDefinition } from '@/shared/api/endpoints/work-regimes';
import ConfirmIcon from '@/shared/assets/icons/ic-confirm.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { hasValue, hasValueNotEmpty } from '@/shared/lib/has-value';
import { useTimezone } from '@/shared/lib/hooks/useTimezone';
import { type DateType } from '@/shared/lib/timezone';
import { AppButton } from '@/shared/ui/AppButton';
import { DatePicker, RangeDatePicker } from '@/shared/ui/DatePicker';
import { Radio } from '@/shared/ui/Radio';
import { TextInput } from '@/shared/ui/TextInput';

import styles from './ShiftCalendar.module.css';

/**
 * Представляет свойства компонента календаря для выбора диапазона смен.
 */
interface CalendarProps {
  /** Возвращает список смен в режиме работы предприятия. */
  readonly shiftDefinitions: readonly ShiftDefinition[];
  /** Возвращает делегат, вызываемый при изменении состояния фильтра. */
  readonly onFilterChange: (startDate: Date, endDate: Date) => void;
  /** Возвращает режим фильтра. */
  readonly mode: 'singleShift' | 'multiShift';
}

/**
 * Представляет компонент календаря для выбора диапазона дат с учетом смен.
 */
export function ShiftCalendar(props: CalendarProps) {
  const { shiftDefinitions, onFilterChange, mode } = props;

  const isSingleShiftMode = mode === 'singleShift';

  const tz = useTimezone();

  const initialValues = (() => {
    const shiftInfo = getShiftByDate(new Date(), shiftDefinitions);

    return {
      checkedShift: shiftInfo?.shiftNum,
      startInput: hasValue(shiftInfo?.startTime) ? tz.utcToDatetimeLocal(shiftInfo.startTime.toISOString()) : '',
      endInput: hasValue(shiftInfo?.endTime) ? tz.utcToDatetimeLocal(shiftInfo.endTime.toISOString()) : '',
      calendarDate: hasValue(shiftInfo?.startTime) ? format(new Date(shiftInfo.shiftDate), 'yyyy-MM-dd') : '',
    };
  })();

  const [startInput, setStartInput] = useState({
    value: initialValues.startInput,
    checkedShift: initialValues.checkedShift,
    checked: isSingleShiftMode,
    isInvalid: false,
  });
  const [endInput, setEndInput] = useState({
    value: initialValues.endInput,
    checkedShift: initialValues.checkedShift,
    checked: false,
    isInvalid: false,
  });
  const [calendarDate, setCalendarDate] = useState({
    start: initialValues.calendarDate,
    end: initialValues.calendarDate,
  });

  const onShiftChange = (value: string) => {
    const checkedShiftNum = Number(value);

    setStartInput((prevState) => {
      const date = new Date(new Date(tz.datetimeLocalToUTC(prevState.value)).getTime());

      const shiftsInfo = getShiftsByDate(date, shiftDefinitions);

      const shiftInfo = shiftsInfo.find((item) => item.shiftNum === checkedShiftNum);

      const newTimeValue = shiftInfo ? tz.format(new Date(shiftInfo.startTime), "yyyy-MM-dd'T'HH:mm") : '';

      return {
        ...prevState,
        value: prevState.checked ? newTimeValue : prevState.value,
        checkedShift: prevState.checked ? checkedShiftNum : prevState.checkedShift,
      };
    });

    setEndInput((prevState) => {
      const date = new Date(new Date(tz.datetimeLocalToUTC(prevState.value)).getTime() - END_SHIFT_OFFSET);

      const shiftsInfo = getShiftsByDate(date, shiftDefinitions);

      const shiftInfo = shiftsInfo.find((item) => item.shiftNum === checkedShiftNum);

      const newTimeValue = shiftInfo ? tz.format(new Date(shiftInfo.endTime), "yyyy-MM-dd'T'HH:mm") : '';

      return {
        ...prevState,
        value: prevState.checked || isSingleShiftMode ? newTimeValue : prevState.value,
        checkedShift: prevState.checked ? checkedShiftNum : prevState.checkedShift,
      };
    });
  };

  const onChangeStartInputValue = (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    const isBadInput = e.currentTarget.validity.badInput;

    const shiftInfo = getShiftByDate(new Date(tz.datetimeLocalToUTC(value)), shiftDefinitions);

    setStartInput((prevState) => ({
      ...prevState,
      value,
      isInvalid: isBadInput,
      checkedShift: shiftInfo?.shiftNum,
    }));

    if (shiftInfo?.shiftDate) {
      setCalendarDate((prevState) => ({ ...prevState, start: format(new Date(shiftInfo.shiftDate), 'yyyy-MM-dd') }));
    }
  };

  const onChangeEndInputValue = (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    const isBadInput = e.currentTarget.validity.badInput;

    const shiftInfo = getShiftByDate(new Date(tz.datetimeLocalToUTC(value)), shiftDefinitions);

    setEndInput((prevState) => ({ ...prevState, value, isInvalid: isBadInput, checkedShift: shiftInfo?.shiftNum }));

    if (shiftInfo?.shiftDate) {
      setCalendarDate((prevState) => ({ ...prevState, end: format(new Date(shiftInfo.shiftDate), 'yyyy-MM-dd') }));
    }
  };

  const onDateChange = (value: string | null) => {
    const hasDate = hasValueNotEmpty(value);

    if (hasDate) {
      const shiftsInfo = getShiftsByDate(new Date(value), shiftDefinitions);

      const shiftInfo = shiftsInfo.find((item) => item.shiftNum === startInput.checkedShift);

      const timeForInputs = getShiftTime(tz.format, shiftInfo);

      setStartInput((prevState) => ({
        ...prevState,
        value: timeForInputs.start,
      }));

      setEndInput((prevState) => ({
        ...prevState,
        value: timeForInputs.end,
      }));
    }

    setCalendarDate({ start: hasDate ? value : '', end: hasDate ? value : '' });
  };

  const onDateRangeChange = (value: DatesRangeValue<string>) => {
    const start = value.at(0);
    const end = value.at(1);

    const hasStart = hasValueNotEmpty(start);
    const hasEnd = hasValueNotEmpty(end);

    const startShiftInfo = hasStart ? getShiftByDate(new Date(start), shiftDefinitions) : undefined;
    const timeForStartInput = getShiftTime(tz.format, startShiftInfo);

    const endShiftInfo = hasEnd ? getShiftByDate(new Date(end), shiftDefinitions) : undefined;
    const timeForEndInput = getShiftTime(tz.format, endShiftInfo);

    if (hasStart) {
      setStartInput((prevState) => ({
        ...prevState,
        value: timeForStartInput.start,
        checkedShift: startShiftInfo?.shiftNum,
      }));
    }

    if (hasEnd) {
      setEndInput((prevState) => ({
        ...prevState,
        value: timeForEndInput.end,
        checkedShift: endShiftInfo?.shiftNum,
      }));
    } else if (hasStart) {
      setEndInput((prevState) => ({
        ...prevState,
        value: timeForStartInput.end,
        checkedShift: startShiftInfo?.shiftNum,
      }));
    }

    setCalendarDate({ start: hasStart ? start : '', end: hasEnd ? end : '' });
  };

  const onConfirm = () => {
    const endDateWithCorrection = new Date(
      new Date(tz.datetimeLocalToUTC(endInput.value)).getTime() - END_SHIFT_OFFSET,
    );

    onFilterChange(new Date(tz.datetimeLocalToUTC(startInput.value)), endDateWithCorrection);
  };

  const isConfirmButtonDisabled = !hasValueNotEmpty(startInput.value) || !hasValueNotEmpty(endInput.value);

  const isDisabledShiftsGroup = !(startInput.checked || endInput.checked) && !isSingleShiftMode;

  return (
    <div className={styles.root}>
      {!isSingleShiftMode && (
        <div className={styles.inputs_container}>
          <TextInput
            type="datetime-local"
            label="Начало"
            labelPosition="vertical"
            max="9999-12-31T23:59"
            value={startInput.value}
            onChange={onChangeStartInputValue}
            classNames={{
              root: styles.datetime_root,
              label: styles.datetime_label,
              wrapper: cn(styles.datetime_wrapper, { [styles.checked]: startInput.checked }),
            }}
            onSelect={() => {
              setStartInput((prevState) => ({ ...prevState, checked: true }));
              setEndInput((prevState) => ({ ...prevState, checked: false }));
            }}
            error={startInput.isInvalid ? 'Введена некорректная дата' : undefined}
          />
          <TextInput
            type="datetime-local"
            label="Конец"
            labelPosition="vertical"
            max="9999-12-31T23:59"
            value={endInput.value}
            onChange={onChangeEndInputValue}
            classNames={{
              root: styles.datetime_root,
              label: styles.datetime_label,
              wrapper: cn(styles.datetime_wrapper, { [styles.checked]: endInput.checked }),
            }}
            onSelect={() => {
              setStartInput((prevState) => ({ ...prevState, checked: false }));
              setEndInput((prevState) => ({ ...prevState, checked: true }));
            }}
            error={endInput.isInvalid ? 'Введена некорректная дата' : undefined}
          />
        </div>
      )}
      <div className={styles.calendar_container}>
        {isSingleShiftMode ? (
          <DatePicker
            highlightToday={true}
            value={calendarDate.start}
            onChange={onDateChange}
          />
        ) : (
          <RangeDatePicker
            highlightToday={true}
            value={[calendarDate.start, calendarDate.end]}
            onChange={onDateRangeChange}
          />
        )}

        <div className={styles.buttons_container}>
          <Radio.Group
            value={startInput.checked ? String(startInput.checkedShift) : String(endInput.checkedShift)}
            onChange={onShiftChange}
            disabled={isDisabledShiftsGroup}
          >
            <div className={styles.shift_buttons_container}>
              {shiftDefinitions.map((item) => (
                <Radio
                  key={item.shift_num}
                  size="xs"
                  label={`Смена ${item.shift_num}`}
                  value={item.shift_num}
                  classNames={{
                    labelWrapper: styles.radio_label_wrapper,
                    label: styles.radio_label,
                    inner: styles.radio_inner,
                  }}
                  className={cn(
                    {
                      [styles.shift_checked]:
                        (startInput.checked && startInput.checkedShift === item.shift_num) ||
                        (endInput.checked && endInput.checkedShift === item.shift_num),
                    },
                    { [styles.shift_disabled]: isDisabledShiftsGroup },
                  )}
                />
              ))}
            </div>
          </Radio.Group>
          <div className={styles.confirm_button_container}>
            <AppButton
              size="xs"
              onlyIcon
              title="Применить фильтр"
              onClick={onConfirm}
              disabled={isConfirmButtonDisabled}
            >
              <ConfirmIcon />
            </AppButton>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Возвращает время смены. */
function getShiftTime(format: (date: DateType, formatStr?: string) => string, shiftInfo?: ShiftInfo) {
  return {
    start: shiftInfo ? format(shiftInfo.startTime, "yyyy-MM-dd'T'HH:mm") : '',
    end: shiftInfo ? format(shiftInfo.endTime, "yyyy-MM-dd'T'HH:mm") : '',
  };
}
