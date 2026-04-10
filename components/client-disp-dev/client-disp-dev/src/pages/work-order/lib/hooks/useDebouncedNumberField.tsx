import { useDebouncedCallback } from '@mantine/hooks';
import { useRef } from 'react';
import type { NumberFormatValues, SourceInfo } from 'react-number-format/types/types';

import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';

import { updateLinkedField } from '../../model/thunks';
import type { LinkedField, TaskIdentifier } from '../../model/types';

const DEBOUNCE_MS = 300;

/**
 * Представляет опции для хука для обработки числовых полей.
 */
interface UseLinkedFieldOptions extends TaskIdentifier {
  readonly value: number | null;
  readonly field: LinkedField;
}

/**
 * Хук для связанных числовых полей (volume, weight, plannedTripsCount).
 * При изменении одного поля автоматически пересчитывает остальные.
 */
export function useDebouncedNumberField({ value, field, vehicleId, taskId }: UseLinkedFieldOptions) {
  const dispatch = useAppDispatch();

  const lastValueRef = useRef(value);
  lastValueRef.current = value;

  const debouncedUpdate = useDebouncedCallback((newValue: number | null) => {
    if (newValue === lastValueRef.current) return;

    dispatch(updateLinkedField({ vehicleId, taskId, field, value: newValue }));
  }, DEBOUNCE_MS);

  const onValueChange = (values: NumberFormatValues, sourceInfo: SourceInfo) => {
    // Игнорируем изменения не от пользователя (например, при изменении props)
    // sourceInfo.event существует только при пользовательском вводе
    if (!sourceInfo.event) return;

    const numericValue = hasValue(values.floatValue) ? values.floatValue : null;
    debouncedUpdate(numericValue);
  };

  return { value: hasValue(value) ? value : '', onValueChange };
}
