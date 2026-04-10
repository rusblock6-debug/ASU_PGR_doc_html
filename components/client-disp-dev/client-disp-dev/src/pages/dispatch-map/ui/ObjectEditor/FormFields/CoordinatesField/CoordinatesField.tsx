import { Controller, type ControllerRenderProps, useFormContext, useWatch } from 'react-hook-form';

import LocationIcon from '@/shared/assets/icons/ic-location.svg?react';
import TrashIcon from '@/shared/assets/icons/ic-trash.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { hasValue, hasValueNotEmpty } from '@/shared/lib/has-value';
import { mantineInputWrapper } from '@/shared/styles/mantine';
import { AppButton } from '@/shared/ui/AppButton';
import { NumberInput } from '@/shared/ui/NumberInput';

import type { FormFieldProps } from '../types';

import styles from './CoordinatesField.module.css';

/** Тип значения для одной оси координаты в форме. */
type CoordinateAxisValue = string | number | undefined;

/** Свойства поля ввода координат (широта и долгота). */
interface CoordinatesFieldProps extends Omit<FormFieldProps, 'name'> {
  /** Возвращает имя поля широты. */
  readonly xName: string;
  /** Возвращает имя поля долготы. */
  readonly yName: string;
  /** Возвращает делегат, вызываемый при нажатии на кнопку размещения объекта на карте. */
  readonly onPlacementClick: () => void;
  /** Возвращает делегат, вызываемый при нажатии на кнопку очистки координат (если координаты уже заданы). */
  readonly onClearClick?: () => void;
}

/** Поле ввода координат (широта и долгота). */
export function CoordinatesField({
  xName,
  yName,
  label,
  required,
  readOnly,
  disabled,
  onPlacementClick,
  onClearClick,
}: CoordinatesFieldProps) {
  const { control } = useFormContext();

  const x = useWatch({ control, name: xName }) as CoordinateAxisValue;
  const y = useWatch({ control, name: yName }) as CoordinateAxisValue;
  const hasCoordinates = hasValueNotEmpty(x) && hasValueNotEmpty(y);
  const isClearMode = hasCoordinates && hasValue(onClearClick);

  const handleChange = (field: ControllerRenderProps, value: number | string) => {
    field.onChange(value);
  };

  return (
    <div className={styles.text_input_root}>
      <p className={cn(styles.text_input_label, mantineInputWrapper.label)}>
        {label}
        {required ? ' *' : ''}
      </p>
      <div className={styles.inputs_container}>
        <Controller
          name={xName}
          control={control}
          render={({ field, fieldState }) => (
            <NumberInput
              value={(field.value as string | number | undefined) ?? ''}
              onChange={(value) => handleChange(field, value)}
              onBlur={field.onBlur}
              labelPosition="vertical"
              withAsterisk={required}
              error={fieldState.error?.message}
              readOnly={readOnly}
              disabled={disabled}
              placeholder="Широта"
              min={0}
            />
          )}
        />
        <Controller
          name={yName}
          control={control}
          render={({ field, fieldState }) => (
            <NumberInput
              value={(field.value as string | number | undefined) ?? ''}
              onChange={(value) => handleChange(field, value)}
              onBlur={field.onBlur}
              labelPosition="vertical"
              withAsterisk={required}
              error={fieldState.error?.message}
              readOnly={readOnly}
              disabled={disabled}
              placeholder="Долгота"
              min={0}
            />
          )}
        />
        <AppButton
          size="xs"
          className={styles.map_button}
          onClick={isClearMode ? onClearClick : onPlacementClick}
          disabled={disabled}
        >
          {isClearMode ? <TrashIcon /> : <LocationIcon />}
        </AppButton>
      </div>
    </div>
  );
}
