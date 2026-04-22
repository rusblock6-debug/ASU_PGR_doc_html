import { ruPlural } from '@/shared/lib/plural';
import { toast } from '@/shared/ui/Toast';

/** Кастомные сообщения уведомлений для операции удаления. */
export interface DeleteToastMessages {
  /** Показать уведомление при ожидании завершения запроса. */
  readonly loading?: (count: number) => string;
  /** Показать уведомление при успешном завершении запроса. */
  readonly success?: (count: number) => string;
  /** Показать уведомление при неуспешном завершении запроса. */
  readonly error?: string;
}

/**
 * Обёртка для операции удаления с автоматическим отображением toast.
 */
export function deleteWithToast(promiseOrVoid: Promise<unknown> | void, count: number, messages?: DeleteToastMessages) {
  const promise = promiseOrVoid ?? Promise.resolve();

  return toast.promise(promise, {
    loading: {
      message:
        messages?.loading?.(count) ?? `Удаление ${count}\u00A0${ruPlural(count, 'объекта', 'объектов', 'объектов')}`,
    },
    success: {
      message:
        messages?.success?.(count) ??
        `${count}\u00A0${ruPlural(count, 'объект', 'объекта', 'объектов')} ${ruPlural(count, 'удалён', 'удалены', 'удалено')} из справочника`,
    },
    error: {
      message: messages?.error ?? 'Ошибка удаления',
    },
  });
}
