import { useDebouncedCallback } from '@mantine/hooks';
import { useRef } from 'react';

import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';

import { updateTaskField } from '../../model/thunks';
import type { TaskIdentifier } from '../../model/types';

const DEBOUNCE_MS = 300;

/**
 * Представляет опции для хука обработки текстовых полей.
 */
interface UseDebouncedTextFieldOptions extends TaskIdentifier {
  readonly value: string | null;
  readonly field: 'message';
}

/**
 * Хук для текстовых полей с задержкой сохранения.
 */
export function useDebouncedTextField({ value, field, vehicleId, taskId }: UseDebouncedTextFieldOptions) {
  const dispatch = useAppDispatch();

  const lastValueRef = useRef(value);
  lastValueRef.current = value;

  const debouncedUpdate = useDebouncedCallback((newValue: string | null) => {
    if (newValue === lastValueRef.current) return;
    dispatch(updateTaskField({ vehicleId, taskId, field, value: newValue }));
  }, DEBOUNCE_MS);

  const onChange = (newValue: string) => {
    debouncedUpdate(newValue || null);
  };

  return { value: hasValue(value) ? value : '', onChange };
}
