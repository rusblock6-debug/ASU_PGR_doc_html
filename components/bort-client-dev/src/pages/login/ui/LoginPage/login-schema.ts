import { z } from 'zod';

import { STRING_VALIDATION } from '@/shared/lib/validation';

/**
 * Схема мок-формы входа (логин и пароль).
 */
export const loginFormSchema = z.object({
  login: STRING_VALIDATION,
  password: STRING_VALIDATION,
});

export type LoginFormValues = z.infer<typeof loginFormSchema>;
