import { PinPageButton } from '@/features/pin-page';

import InfoMinus from '@/shared/assets/icons/ic-minus.svg?react';
import InfoPlus from '@/shared/assets/icons/ic-plus.svg?react';
import RulerIcon from '@/shared/assets/icons/ic-ruler.svg?react';
import { useConfirm } from '@/shared/lib/confirm';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { AppRoutes } from '@/shared/routes/router';
import { AppButton } from '@/shared/ui/AppButton';

import { selectIsGraphDirty } from '../../model/graph';
import { selectIsGraphEditActive, selectIsRulerActive } from '../../model/selectors';
import { mapActions } from '../../model/slice';
import { useMapCameraContext } from '../MapCameraProvider';

import { MapViewSwitcher } from './MapViewSwitcher';
import styles from './Toolbar.module.css';

/**
 * Панель инструментов в правом верхнем углу карты.
 */
export function Toolbar() {
  const dispatch = useAppDispatch();
  const isRulerActive = useAppSelector(selectIsRulerActive);
  const isGraphEditActive = useAppSelector(selectIsGraphEditActive);
  const isGraphDirty = useAppSelector(selectIsGraphDirty);
  const { zoomIn, zoomOut } = useMapCameraContext();
  const confirm = useConfirm();

  const handleRulerClick = async () => {
    if (isGraphEditActive && isGraphDirty) {
      const confirmed = await confirm({
        title: 'Режим редактирования дорог активен',
        message:
          'Для использования линейки необходимо выйти из режима редактирования дорог. Несохранённые изменения будут потеряны.',
        confirmText: 'Продолжить',
        cancelText: 'Отмена',
        size: 'md',
      });

      if (!confirmed) return;
    }

    if (isGraphEditActive) {
      dispatch(mapActions.toggleGraphEdit());
    }

    dispatch(mapActions.toggleRuler());
  };

  return (
    <div className={styles.root}>
      <MapViewSwitcher />

      <AppButton
        onlyIcon
        variant={isRulerActive ? 'primary' : 'clear'}
        size="xs"
        title={isRulerActive ? 'Выключить линейку' : 'Включить линейку'}
        onClick={handleRulerClick}
      >
        <RulerIcon />
      </AppButton>

      <div className={styles.zoom_buttons_container}>
        <AppButton
          onlyIcon
          variant="clear"
          size="xs"
          title="Уменьшить масштаб"
          onClick={zoomOut}
        >
          <InfoMinus />
        </AppButton>
        <AppButton
          onlyIcon
          variant="clear"
          size="xs"
          title="Увеличить масштаб"
          onClick={zoomIn}
        >
          <InfoPlus />
        </AppButton>
      </div>

      <PinPageButton pageId={AppRoutes.DISPATCH_MAP} />
    </div>
  );
}
