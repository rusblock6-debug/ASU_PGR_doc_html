import { zodResolver } from '@hookform/resolvers/zod';
import { useForm, type FieldValues, type UseFormProps } from 'react-hook-form';
import type { z } from 'zod';

/**
 * Обёртка над `useForm` с `zodResolver` для единообразных форм в приложении.
 */
export function useAppForm<TFieldValues extends FieldValues>(
  /** Схема с совпадающими input/output (типичный `z.object`). */
  schema: z.ZodType<TFieldValues, TFieldValues>,
  props?: Omit<UseFormProps<TFieldValues>, 'resolver'>,
) {
  return useForm<TFieldValues>({
    resolver: zodResolver(schema),
    ...props,
  });
}
