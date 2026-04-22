import { Controller, type ControllerRenderProps, type FieldValues } from 'react-hook-form';

import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { Select } from '@/shared/ui/Select';

import { isSelectMeta } from '../../lib/column-utils';
import { formatSelectValue } from '../../lib/formatters';
import { useFormField } from '../../lib/hooks/useFormField';
import type { FormFieldProps } from '../../types';

type FieldOnChange = ControllerRenderProps<FieldValues, string>['onChange'];

/** Компонент для отображения данных в виде выпадающего списка. */
export function SelectField({ column, mode }: Readonly<FormFieldProps>) {
  const { columnId, label, isReadOnly, isRequired, control, setValue } = useFormField(column, mode);

  const meta = isSelectMeta(column.meta) ? column.meta : null;
  const { autoFill, options = EMPTY_ARRAY, valueType = 'string' } = meta || {};

  // Извлекаем ключи полей из первой записи autoFill
  const autoFillFields = autoFill ? Object.keys(Object.values(autoFill)[0] ?? {}) : EMPTY_ARRAY;

  const fillRelatedFields = (fillData: Record<string, unknown> | null | undefined) => {
    // Если есть данные — заполняем, иначе сбрасываем все поля в null
    const dataToFill = fillData ?? Object.fromEntries(autoFillFields.map((key) => [key, null]));

    Object.entries(dataToFill).forEach(([fieldKey, fieldValue]) => {
      setValue(fieldKey, fieldValue ?? null, { shouldDirty: true, shouldValidate: true });
    });
  };

  const handleChange = (fieldOnChange: FieldOnChange) => {
    return (value: string | null) => {
      fieldOnChange(formatSelectValue(value, valueType));

      // Автозаполнение связанных полей (при выборе — заполняем, при сбросе — обнуляем)
      if (autoFillFields.length > 0) {
        const fillData = hasValue(value) ? autoFill?.[value] : null;
        fillRelatedFields(fillData);
      }
    };
  };

  return (
    <Controller
      name={columnId}
      control={control}
      render={({ field, fieldState }) => (
        <Select
          {...field}
          withAsterisk={isRequired}
          value={hasValue(field.value) ? String(field.value) : null}
          data={[...options]}
          onChange={handleChange(field.onChange)}
          label={label}
          error={fieldState.error?.message}
          readOnly={isReadOnly}
          disabled={isReadOnly}
        />
      )}
    />
  );
}
