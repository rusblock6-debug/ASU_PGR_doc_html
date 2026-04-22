import { PinPageButton } from '@/features/pin-page';

import InfoMinus from '@/shared/assets/icons/ic-minus.svg?react';
import InfoPlus from '@/shared/assets/icons/ic-plus.svg?react';
import RulerIcon from '@/shared/assets/icons/ic-ruler.svg?react';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { AppRoutes } from '@/shared/routes/router';
import { AppButton } from '@/shared/ui/AppButton';

import { useExitGraphEdit } from '../../lib/hooks/useExitGraphEdit';
import { selectIsRulerActive } from '../../model/selectors';
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
  const { zoomIn, zoomOut } = useMapCameraContext();
  const exitGraphEdit = useExitGraphEdit();

  const handleRulerClick = async () => {
    const canProceed = await exitGraphEdit(
      'Для использования линейки необходимо выйти из режима редактирования дорог. Несохранённые изменения будут потеряны.',
    );
    if (!canProceed) return;

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
