import { createContext, useContext, useState, type PropsWithChildren } from 'react';

import { ConfirmModal } from '@/shared/ui/ConfirmModal';

import type { ConfirmOptions, ConfirmContextValue } from './types';

const ConfirmContext = createContext<ConfirmContextValue | null>(null);

/** Внутреннее состояние модального окна подтверждения. */
interface ConfirmState {
  /** Параметры отображения модального окна. */
  readonly options: ConfirmOptions;
  /** Функция резолва промиса, вызывается при подтверждении или отмене. */
  readonly resolve: (value: boolean) => void;
}

/**
 * Провайдер для модального окна подтверждения.
 * Оборачивает приложение и предоставляет доступ к функции `confirm` через хук `useConfirm`.
 */
export function ConfirmProvider({ children }: Readonly<PropsWithChildren>) {
  const [isOpen, setIsOpen] = useState(false);
  const [state, setState] = useState<ConfirmState | null>(null);

  const confirm = (options: ConfirmOptions) => {
    return new Promise((resolve) => {
      setState((prevState) => {
        prevState?.resolve(false);
        return { options, resolve };
      });
      setIsOpen(true);
    });
  };

  const handleConfirm = () => {
    state?.resolve(true);
    setIsOpen(false);
  };

  const handleClose = () => {
    state?.resolve(false);
    setIsOpen(false);
  };

  const handleTransitionEnd = () => {
    if (!isOpen) {
      setState(null);
    }
  };

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}

      <ConfirmModal
        isOpen={isOpen}
        title={state?.options.title}
        message={state?.options.message ?? ''}
        confirmButtonText={state?.options.confirmText ?? 'Подтвердить'}
        closeButtonText={state?.options.cancelText ?? 'Отмена'}
        size={state?.options.size ?? 'sm'}
        onConfirm={handleConfirm}
        onClose={handleClose}
        onTransitionEnd={handleTransitionEnd}
      />
    </ConfirmContext.Provider>
  );
}

/**
 * Хук для вызова модального окна подтверждения.
 *
 * @returns Функция `confirm`, открывающая модальное окно и возвращающая `Promise<boolean>`.
 *
 * @throws {Error} Если хук используется вне `ConfirmProvider`.
 *
 * @example
 * const confirm = useConfirm();
 *
 * const handleDelete = async () => {
 *   const isConfirmed = await confirm({
 *     title: 'Удаление',
 *     message: 'Вы уверены, что хотите удалить?',
 *     confirmText: 'Удалить',
 *     cancelText: 'Отмена',
 *   });
 *
 *   if (isConfirmed) {
 *     // выполнить удаление
 *   }
 * };
 */
export function useConfirm() {
  const context = useContext(ConfirmContext);

  if (!context) {
    throw new Error('useConfirm must be used within ConfirmProvider');
  }

  return context.confirm;
}
