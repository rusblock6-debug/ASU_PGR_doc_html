import { Controller, type ControllerRenderProps } from 'react-hook-form';

import LocationIcon from '@/shared/assets/icons/ic-location.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { mantineInputWrapper } from '@/shared/styles/mantine';
import { AppButton } from '@/shared/ui/AppButton';
import { NumberInput } from '@/shared/ui/NumberInput';

import { useFormField } from '../../lib/hooks/useFormField';
import type { FormFieldProps } from '../../types';

import styles from './CoordinatesField.module.css';

/** Поле ввода координат (широта и долгота). */
export function CoordinatesField({ column, mode }: Readonly<FormFieldProps>) {
  const { columnId, label, isReadOnly, isRequired, control, trigger } = useFormField(column, mode);

  const latField = `${columnId}.lat`;
  const lonField = `${columnId}.lon`;

  const handleChange = (field: ControllerRenderProps, value: number | string) => {
    field.onChange(value);
    void trigger(columnId);
  };

  return (
    <div className={styles.text_input_root}>
      <p className={cn(styles.text_input_label, mantineInputWrapper.label)}>
        {label}
        {isRequired ? ' *' : ''}
      </p>
      <div className={styles.inputs_container}>
        <Controller
          name={latField}
          control={control}
          render={({ field, fieldState }) => (
            <NumberInput
              value={(field.value as number | string) ?? ''}
              onChange={(value) => handleChange(field, value)}
              onBlur={field.onBlur}
              labelPosition="vertical"
              withAsterisk={isRequired}
              error={fieldState.error?.message}
              readOnly={isReadOnly}
              disabled={isReadOnly}
              placeholder="Широта"
              min={0}
            />
          )}
        />
        <Controller
          name={lonField}
          control={control}
          render={({ field, fieldState }) => (
            <NumberInput
              value={(field.value as number | string) ?? ''}
              onChange={(value) => handleChange(field, value)}
              onBlur={field.onBlur}
              labelPosition="vertical"
              withAsterisk={isRequired}
              error={fieldState.error?.message}
              readOnly={isReadOnly}
              disabled={isReadOnly}
              placeholder="Долгота"
              min={0}
            />
          )}
        />
        <AppButton
          size="xs"
          className={styles.map_button}
        >
          <LocationIcon />
        </AppButton>
      </div>
    </div>
  );
}
