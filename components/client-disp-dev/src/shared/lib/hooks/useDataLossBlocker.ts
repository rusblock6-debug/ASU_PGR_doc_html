import { useCallback, useEffect, useMemo, useState } from 'react';
import { useBlocker } from 'react-router-dom';

import { useConfirm } from '@/shared/lib/confirm';

/**
 * Представляет свойства хука {@link useDataLossBlocker}.
 */
interface UseDataLossBlockerOptions {
  /** Флаг наличия несохранённых изменений */
  readonly hasUnsavedChanges: boolean;
  /** Заголовок окна подтверждения */
  readonly title?: string;
  /** Сообщение в окне подтверждения */
  readonly message?: string;
  /** Колбэк для сброса состояния (вызывается при подтверждении) */
  readonly onReset?: () => void;
}

/**
 * Блокирует навигацию при наличии несохранённых данных.
 * Показывает confirm при попытке уйти со страницы или закрыть вкладку.
 */
export function useDataLossBlocker({ hasUnsavedChanges, title, message, onReset }: UseDataLossBlockerOptions) {
  const confirm = useConfirm();
  const blocker = useBlocker(hasUnsavedChanges);

  const modalText = useMemo(() => getModalText(title, message), [title, message]);

  const [showConfirm, setShowConfirm] = useState(false);

  const handleBeforeUnload = useCallback(
    (event: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        event.preventDefault();
      }
    },
    [hasUnsavedChanges],
  );

  useEffect(() => {
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [handleBeforeUnload]);

  useEffect(() => {
    if (blocker.state === 'blocked') {
      setShowConfirm(true);
    }
  }, [blocker.state]);

  const handleConfirm = useCallback(() => {
    if (blocker.state === 'blocked') {
      setShowConfirm(false);
      onReset?.();
      blocker.proceed();
    }
  }, [blocker, onReset]);

  const handleCancel = useCallback(() => {
    if (blocker.state === 'blocked') {
      setShowConfirm(false);
      blocker.reset();
    }
  }, [blocker]);

  const confirmFn = useCallback(async () => {
    const isConfirmed = await confirm({ title: modalText.title, message: modalText.message });
    if (isConfirmed) {
      handleConfirm();
    } else {
      handleCancel();
    }
  }, [confirm, handleCancel, handleConfirm, modalText.message, modalText.title]);

  useEffect(() => {
    if (showConfirm) {
      void confirmFn();
    }
  }, [confirmFn, showConfirm]);

  const forceBlocker = useCallback(async () => {
    if (!hasUnsavedChanges) {
      return true;
    }

    const isConfirmed = await confirm({ title: modalText.title, message: modalText.message });
    if (isConfirmed) {
      onReset?.();
      return true;
    }

    return false;
  }, [confirm, hasUnsavedChanges, modalText.title, modalText.message, onReset]);

  return { forceBlocker };
}

/**
 * Возвращает тексты для модального окна с фоллбэком на значения по умолчанию.
 */
function getModalText(title?: string, message?: string) {
  return {
    title: title ?? 'Внимание!',
    message: message ?? 'Все несохранённые изменения будут утеряны.',
  };
}
