import { useConfirm } from '@/shared/lib/confirm';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { graphEditActions, selectIsColorDirty, selectIsGraphDirty } from '../../model/graph';
import { selectIsGraphEditActive } from '../../model/selectors';
import { mapActions } from '../../model/slice';

/**
 * Хук для безопасного выхода из режима редактирования дорожного графа и/или цвета дороги.
 *
 * Возвращает асинхронную функцию, которая:
 * - возвращает `true`, если редактор не активен и цвет не изменён, или пользователь подтвердил выход;
 * - возвращает `false`, если пользователь отменил выход.
 */
export function useExitGraphEdit() {
  const dispatch = useAppDispatch();
  const isGraphEditActive = useAppSelector(selectIsGraphEditActive);
  const isGraphDirty = useAppSelector(selectIsGraphDirty);
  const isColorDirty = useAppSelector(selectIsColorDirty);
  const confirm = useConfirm();

  return async (message: string) => {
    if (!isGraphEditActive && !isColorDirty) return true;

    if (isGraphDirty || isColorDirty) {
      const confirmed = await confirm({
        title: 'Режим редактирования дорог активен',
        message,
        confirmText: 'Продолжить',
        cancelText: 'Отмена',
        size: 'md',
      });
      if (!confirmed) return false;
    }

    dispatch(graphEditActions.resetDraft());

    if (isGraphEditActive) dispatch(mapActions.toggleGraphEdit());

    return true;
  };
}
