import { ruPlural } from '@/shared/lib/plural';
import { toast } from '@/shared/ui/Toast';

/**
 * Обёртка для операции удаления с автоматическим отображением toast.
 */
export function deleteWithToast(promiseOrVoid: Promise<unknown> | void, count: number) {
  const promise = promiseOrVoid ?? Promise.resolve();

  return toast.promise(promise, {
    loading: {
      message: `Удаление ${count}\u00A0${ruPlural(count, 'объекта', 'объектов', 'объектов')}`,
    },
    success: {
      message: `${count}\u00A0${ruPlural(count, 'объект', 'объекта', 'объектов')} ${ruPlural(count, 'удалён', 'удалены', 'удалено')} из справочника`,
    },
    error: {
      message: 'Ошибка удаления',
    },
  });
}
