import { zodResolver } from '@hookform/resolvers/zod';
import React, { useEffect } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { z } from 'zod';

import { cn } from '@/shared/lib/classnames-utils';
import { getErrorMessage } from '@/shared/lib/error-message';
import { AppButton } from '@/shared/ui/AppButton';

import { getFieldDefaultValue, getFieldValidationSchema } from '../../config/form-field-registry';
import { getColumnValue, isColumnRequired } from '../../lib/column-utils';
import { ColumnDataTypes, type ColumnDef } from '../../types';
import { FormError } from '../FormError';
import { FormField } from '../FormField';

import styles from './RecordForm.module.css';

interface RecordFormProps<TData> {
  /** Определения колонок таблицы для генерации полей формы. */
  readonly columns: ColumnDef<TData>[];
  /** Начальные данные для редактирования. */
  readonly initialData?: Partial<TData>;
  /** Callback при отправке формы. */
  readonly onSubmit: (data: Partial<TData>) => void | Promise<void>;
  /** Callback при изменении состояния формы (есть ли несохранённые изменения). */
  readonly onDirtyChange?: (isDirty: boolean) => void;
  /** Режим формы: добавление или редактирование. */
  readonly mode?: 'add' | 'edit';
}

/**
 * Универсальная форма для добавления и редактирования записей таблицы.
 * Автоматически генерирует поля на основе form-field-registry.ts.
 */
export function RecordForm<TData>({
  columns,
  initialData,
  onSubmit,
  onDirtyChange,
  mode = 'add',
}: RecordFormProps<TData>) {
  const editableColumns = columns.filter(
    (col): col is ColumnDef<TData> & { accessorKey: string } =>
      'accessorKey' in col && Boolean(col.accessorKey) && !(mode === 'add' && col.meta?.hideOnCreate),
  );

  const { schemaEntries, crossValidators } = editableColumns.reduce<{
    schemaEntries: [string, z.ZodType][];
    crossValidators: {
      columnId: string;
      validate: NonNullable<(typeof editableColumns)[0]['meta']>['crossValidate'];
    }[];
  }>(
    (acc, column) => {
      const columnId = String(column.accessorKey);
      const dataType = column.meta?.dataType ?? ColumnDataTypes.TEXT;
      const isRequired = isColumnRequired(column.meta);

      acc.schemaEntries.push([columnId, getFieldValidationSchema(dataType, isRequired, column.meta)]);

      if (column.meta?.crossValidate) {
        acc.crossValidators.push({ columnId, validate: column.meta.crossValidate });
      }

      return acc;
    },
    { schemaEntries: [], crossValidators: [] },
  );

  const baseSchema = z.object(Object.fromEntries(schemaEntries));

  const validationSchema =
    crossValidators.length === 0
      ? baseSchema
      : baseSchema.superRefine((data, ctx) => {
          for (const { columnId, validate } of crossValidators) {
            if (!validate) continue;

            const error = validate(data[columnId], data);
            if (error) {
              ctx.addIssue({ code: 'custom', message: error, path: [columnId] });
            }
          }
        });

  const defaultValues = Object.fromEntries(
    editableColumns.map((column) => {
      const columnId = String(column.accessorKey);
      const dataType = column.meta?.dataType ?? ColumnDataTypes.TEXT;
      const rawValue = initialData ? getColumnValue(column, initialData as TData) : undefined;

      return [columnId, getFieldDefaultValue(dataType, rawValue, column.meta)];
    }),
  );

  const methods = useForm<Record<string, unknown>>({
    resolver: zodResolver(validationSchema) as never,
    defaultValues,
    mode: 'onChange',
  });

  const {
    handleSubmit,
    formState: { isSubmitting, isDirty, isValid },
    setError,
    clearErrors,
  } = methods;

  useEffect(() => {
    onDirtyChange?.(isDirty);
  }, [isDirty, onDirtyChange]);

  const onFormSubmit = async (data: Record<string, unknown>) => {
    try {
      clearErrors('root');
      await onSubmit(data as Partial<TData>);
    } catch (error) {
      setError('root.submitError', {
        type: 'custom',
        message: getErrorMessage(
          error,
          'Неизвестная ошибка: не удалось сохранить данные. Проверьте правильность заполнения полей или попробуйте позже',
        ),
      });
    }
  };

  const handleEnterSubmit = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      event.preventDefault();
    }
  };

  return (
    <FormProvider {...methods}>
      <form
        onSubmit={handleSubmit(onFormSubmit)}
        onKeyDown={handleEnterSubmit}
        className={styles.form}
      >
        <div className={styles.form_body}>
          {editableColumns.map((column, index) => (
            <div
              key={index}
              className={cn({ [styles.form_row_disabled]: column.meta?.readOnly })}
            >
              <FormField
                column={column}
                mode={mode}
              />
            </div>
          ))}

          <div className={styles.actions}>
            <FormError />

            <AppButton
              className={styles.button}
              type="submit"
              variant="primary"
              size="m"
              disabled={isSubmitting || !isDirty || !isValid}
              loading={isSubmitting}
            >
              Сохранить
            </AppButton>
          </div>
        </div>
      </form>
    </FormProvider>
  );
}
