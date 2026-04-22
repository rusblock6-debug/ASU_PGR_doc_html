import { assertNever } from '@/shared/lib/assert-never';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { ResizablePanel } from '@/shared/ui/Resizable';

import { useExitFormEdit } from '../../lib/hooks/useExitFormEdit';
import { useMapPlaces } from '../../lib/hooks/useMapPlaces';
import { useMapVehicles } from '../../lib/hooks/useMapVehicles';
import { selectFormTarget } from '../../model/selectors';
import { mapActions } from '../../model/slice';

import { PlaceForm, VehicleForm } from './forms';
import styles from './ObjectEditor.module.css';

/**
 * Компонент сайдбара для создания или редактирования объектов.
 */
export function ObjectEditor() {
  const dispatch = useAppDispatch();
  const formTarget = useAppSelector(selectFormTarget);
  const { all: vehiclesList } = useMapVehicles();
  const { all: placesList } = useMapPlaces();
  const exitFormEdit = useExitFormEdit();

  const onClose = async (fn?: () => void) => {
    const canProceed = await exitFormEdit('Вы действительно хотите закрыть окно создания/редактирования объекта?');
    if (!canProceed) return;

    dispatch(mapActions.setFormTarget(null));
    dispatch(mapActions.setHasUnsavedChanges(false));
    fn?.();
  };

  const renderForm = () => {
    if (!formTarget) return null;

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
  };

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
      {renderForm()}
    </ResizablePanel>
  );
}
