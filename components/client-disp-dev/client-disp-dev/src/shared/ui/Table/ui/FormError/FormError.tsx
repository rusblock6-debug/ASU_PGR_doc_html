import { useEffect, useState } from 'react';
import { useFormContext } from 'react-hook-form';

import { hasValueNotEmpty } from '@/shared/lib/has-value';
import { ErrorMessage } from '@/shared/ui/ErrorMessage';

/** Время отображения ошибки в миллисекундах */
const DISPLAY_DURATION_MS = 5_000;

/**
 * Компонент для отображения ошибки отправки формы.
 *
 * Автоматически скрывается через {@link DISPLAY_DURATION_MS} мс.
 * При появлении новой ошибки таймер перезапускается.
 *
 * Компонент должен находиться внутри FormProvider, чтобы использовать useFormContext
 */
export function FormError() {
  const {
    formState: { errors },
    clearErrors,
  } = useFormContext();

  const errorMessage = errors.root?.submitError?.message;
  const [visibleMessage, setVisibleMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!hasValueNotEmpty(errorMessage)) {
      setVisibleMessage(null);
      return;
    }

    setVisibleMessage(errorMessage);

    const timerId = setTimeout(() => {
      setVisibleMessage(null);
      clearErrors('root.submitError');
    }, DISPLAY_DURATION_MS);

    return () => clearTimeout(timerId);
  }, [errorMessage, clearErrors]);

  if (!visibleMessage) return null;

  return <ErrorMessage message={visibleMessage} />;
}
