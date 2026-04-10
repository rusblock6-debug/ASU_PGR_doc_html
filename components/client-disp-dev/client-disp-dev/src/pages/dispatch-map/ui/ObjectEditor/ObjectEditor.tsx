import { useCallback, useMemo } from 'react';

import { assertNever } from '@/shared/lib/assert-never';
import { useConfirm } from '@/shared/lib/confirm';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { ResizablePanel } from '@/shared/ui/Resizable';

import { useMapPlaces } from '../../lib/hooks/useMapPlaces';
import { useMapVehicles } from '../../lib/hooks/useMapVehicles';
import { selectFormTarget, selectHasUnsavedChanges } from '../../model/selectors';
import { mapActions } from '../../model/slice';

import { PlaceForm, VehicleForm } from './forms';
import styles from './ObjectEditor.module.css';

/**
 * Компонент сайдбара для создания или редактирования объектов.
 */
export function ObjectEditor() {
  const dispatch = useAppDispatch();
  const formTarget = useAppSelector(selectFormTarget);
  const hasUnsavedChanges = useAppSelector(selectHasUnsavedChanges);
  const confirm = useConfirm();
  const { all: vehiclesList } = useMapVehicles();
  const { all: placesList } = useMapPlaces();

  const onClose = useCallback(
    async (fn?: () => void) => {
      if (hasUnsavedChanges) {
        const isConfirmed = await confirm({
          title: 'Вы действительно хотите закрыть окно создания/редактирования объекта?',
          message: `Текущие изменения будут утеряны.`,
          confirmText: 'Продолжить',
          cancelText: 'Отмена',
          size: 'md',
        });

        if (isConfirmed) {
          dispatch(mapActions.setFormTarget(null));
          dispatch(mapActions.setHasUnsavedChanges(false));
          fn?.();
        }

        return;
      }

      dispatch(mapActions.setFormTarget(null));
      dispatch(mapActions.setHasUnsavedChanges(false));
      fn?.();
    },
    [confirm, dispatch, hasUnsavedChanges],
  );

  const form = useMemo(() => {
    if (!formTarget) {
      return null;
    }

    switch (formTarget.entity) {
      case 'place': {
        const place = placesList.find((item) => item.id === formTarget.id);

        return (
          <PlaceForm
            place={place}
            onClose={onClose}
          />
        );
      }

      case 'vehicle': {
        const vehicle = vehiclesList.find((item) => item.id === formTarget.id);

        return (
          <VehicleForm
            vehicle={vehicle}
            onClose={onClose}
          />
        );
      }

      default:
        assertNever(formTarget.entity);
    }
  }, [formTarget, onClose, placesList, vehiclesList]);

  if (!formTarget) {
    return null;
  }

  return (
    <ResizablePanel
      id="create-edit-form"
      minSize={400}
      maxSize={800}
      defaultSize={500}
      notifyOnResize
      className={styles.root}
    >
      {form}
    </ResizablePanel>
  );
}
