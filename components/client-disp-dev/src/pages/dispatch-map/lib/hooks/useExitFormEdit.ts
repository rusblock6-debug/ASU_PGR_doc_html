import { useConfirm } from '@/shared/lib/confirm';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { selectHasUnsavedChanges } from '../../model/selectors';

/**
 * Хук для проверки несохранённых изменений в форме редактирования/создания объекта перед переходом к другому действию.
 *
 * Возвращает асинхронную функцию, которая:
 * - возвращает `true`, если изменений нет или пользователь подтвердил потерю данных;
 * - возвращает `false`, если пользователь отменил действие.
 */
export function useExitFormEdit() {
  const hasUnsavedChanges = useAppSelector(selectHasUnsavedChanges);
  const confirm = useConfirm();

  return async (title: string) => {
    if (!hasUnsavedChanges) return true;

    const confirmed = await confirm({
      title,
      message: 'Текущие изменения будут утеряны.',
      confirmText: 'Продолжить',
      cancelText: 'Отмена',
      size: 'md',
    });

    return Boolean(confirmed);
  };
}
