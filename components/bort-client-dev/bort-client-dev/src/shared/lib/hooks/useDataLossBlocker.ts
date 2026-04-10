import { useEffect, useRef, useState } from 'react';
import { useBlocker } from 'react-router-dom';

import { useConfirm } from '@/shared/lib/confirm';

/** Опции хука блокировки потери данных при навигации. */
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
  const blockerRef = useRef(blocker);
  blockerRef.current = blocker;

  const [showConfirm, setShowConfirm] = useState(false);

  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        event.preventDefault();
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [hasUnsavedChanges]);

  useEffect(() => {
    if (blocker.state === 'blocked') {
      setShowConfirm(true);
    }
  }, [blocker.state]);

  useEffect(() => {
    if (!showConfirm) return;

    void (async () => {
      const modalText = getModalText(title, message);
      const isConfirmed = await confirm({ title: modalText.title, message: modalText.message });
      const b = blockerRef.current;

      if (isConfirmed) {
        if (b.state === 'blocked') {
          setShowConfirm(false);
          onReset?.();
          b.proceed();
        }
      } else if (b.state === 'blocked') {
        setShowConfirm(false);
        b.reset();
      }
    })();
  }, [showConfirm, title, message, confirm, onReset]);

  const forceBlocker = async () => {
    if (!hasUnsavedChanges) {
      return true;
    }

    const modalText = getModalText(title, message);
    const isConfirmed = await confirm({ title: modalText.title, message: modalText.message });
    if (isConfirmed) {
      onReset?.();
      return true;
    }

    return false;
  };

  return { forceBlocker };
}

/** Возвращает текст модального окна по умолчанию. */
function getModalText(title?: string, message?: string) {
  return {
    title: title ?? 'Внимание!',
    message: message ?? 'Все несохранённые изменения будут утеряны.',
  };
}
