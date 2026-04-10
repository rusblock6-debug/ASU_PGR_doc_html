import { VehicleTypeIcon } from '@/entities/vehicle';

import { useConfirm } from '@/shared/lib/confirm';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { type MapVehicleItem, useMapVehicles } from '../../../../lib/hooks/useMapVehicles';
import { computeGroupVisibility } from '../../../../model/lib/compute-group-visibility';
import {
  selectFormTarget,
  selectHasUnsavedChanges,
  selectHiddenVehicleIds,
  selectMapMode,
  selectSelectedHorizonId,
} from '../../../../model/selectors';
import { mapActions } from '../../../../model/slice';
import { Mode, TreeNode } from '../../../../model/types';
import { AddButton } from '../../AddButton';
import { CollapsibleSection } from '../../CollapsibleSection';
import { ObjectList } from '../ObjectList';

/**
 * Представляет свойства компонента {@link EquipmentSection}.
 */
interface EquipmentSectionProps {
  /** CSS-классы для кастомизации отдельных частей компонента. */
  readonly classNames?: Partial<Record<'root' | 'children', string>>;
}

/**
 * Секция «Оборудование предприятия» в сайдбаре карты — мобильное оборудование (ПДМ, ШАС).
 */
export function EquipmentSection({ classNames }: EquipmentSectionProps) {
  const dispatch = useAppDispatch();
  const { groups, all, sorts } = useMapVehicles();
  const mapMode = useAppSelector(selectMapMode);
  const selectedHorizonId = useAppSelector(selectSelectedHorizonId);
  const hiddenVehicleIds = useAppSelector(selectHiddenVehicleIds);
  const hasUnsavedChanges = useAppSelector(selectHasUnsavedChanges);
  const formTarget = useAppSelector(selectFormTarget);
  const confirm = useConfirm();

  const onAdd = () => {
    dispatch(mapActions.setFormTarget({ entity: 'vehicle', id: null }));
    dispatch(mapActions.setPlacementPlaceToAdd(null));
  };

  const onEdit = (id: number) => {
    dispatch(mapActions.setFormTarget({ entity: 'vehicle', id }));
    dispatch(mapActions.setPlacementPlaceToAdd(null));
  };

  const handleAddClick = async () => {
    if (hasUnsavedChanges && (formTarget?.entity === 'place' || hasValue(formTarget?.id))) {
      const isConfirmed = await confirm({
        title: 'Вы действительно хотите создать новый объект?',
        message: `Текущие изменения будут утеряны.`,
        confirmText: 'Продолжить',
        cancelText: 'Отмена',
        size: 'md',
      });

      if (isConfirmed) {
        onAdd();
      }
      return;
    }

    onAdd();
  };

  const pdmItems = groups.pdm.map(vehicleToObjectItem);
  const shasItems = groups.shas.map(vehicleToObjectItem);

  const pdmIds = groups.pdm.map((item) => item.id);
  const shasIds = groups.shas.map((item) => item.id);
  const allIds = all.map((item) => item.id);

  const pdmCount = pdmItems.length;
  const shasCount = shasItems.length;
  const totalCount = all.length;

  const handleLocate = (id: number) => {
    const vehicle = all.find((item) => item.id === id);
    if (hasValue(vehicle?.horizon_id) && vehicle.horizon_id !== selectedHorizonId) {
      dispatch(mapActions.setSelectedHorizonId(vehicle.horizon_id));
    }

    dispatch(mapActions.setFocusTarget({ entity: 'vehicle', id }));
  };

  const handleToggleVisibility = (id: number) => dispatch(mapActions.toggleVehicleVisibility(id));

  return (
    <CollapsibleSection
      className={classNames?.root}
      groupKey={TreeNode.EQUIPMENT}
      label="Оборудование предприятия"
      count={totalCount}
      visibility={computeGroupVisibility(allIds, hiddenVehicleIds)}
      onToggleVisibility={() => dispatch(mapActions.toggleVehiclesVisibility(allIds))}
      leftSectionComponent={mapMode === Mode.EDIT && <AddButton onClick={handleAddClick} />}
    >
      <CollapsibleSection
        className={classNames?.children}
        groupKey={TreeNode.MOBILE_EQUIPMENT}
        label="Мобильное оборудование"
        count={totalCount}
        visibility={computeGroupVisibility(allIds, hiddenVehicleIds)}
        onToggleVisibility={() => dispatch(mapActions.toggleVehiclesVisibility(allIds))}
      >
        <CollapsibleSection
          className={classNames?.children}
          groupKey={TreeNode.VEHICLES_PDM}
          label="ПДМ"
          count={pdmCount}
          disabled={pdmCount === 0}
          visibility={computeGroupVisibility(pdmIds, hiddenVehicleIds)}
          onToggleVisibility={() => dispatch(mapActions.toggleVehiclesVisibility(pdmIds))}
        >
          <ObjectList
            items={pdmItems}
            hiddenIds={hiddenVehicleIds}
            sortState={sorts.pdm}
            onSortChange={(field) => dispatch(mapActions.toggleGroupSort({ entity: 'vehicle', group: 'pdm', field }))}
            onLocate={handleLocate}
            onToggleVisibility={handleToggleVisibility}
            onEdit={onEdit}
          />
        </CollapsibleSection>

        <CollapsibleSection
          className={classNames?.children}
          groupKey={TreeNode.VEHICLES_SHAS}
          label="ШАС"
          count={shasCount}
          disabled={shasCount === 0}
          visibility={computeGroupVisibility(shasIds, hiddenVehicleIds)}
          onToggleVisibility={() => dispatch(mapActions.toggleVehiclesVisibility(shasIds))}
        >
          <ObjectList
            items={shasItems}
            hiddenIds={hiddenVehicleIds}
            sortState={sorts.shas}
            onSortChange={(field) => dispatch(mapActions.toggleGroupSort({ entity: 'vehicle', group: 'shas', field }))}
            onLocate={handleLocate}
            onToggleVisibility={handleToggleVisibility}
            onEdit={onEdit}
          />
        </CollapsibleSection>
      </CollapsibleSection>
    </CollapsibleSection>
  );
}

/**
 * Преобразует технику в элемент списка объектов.
 */
function vehicleToObjectItem(vehicle: MapVehicleItem) {
  return {
    id: vehicle.id,
    name: vehicle.name,
    horizon: vehicle.horizon_name,
    icon: (
      <VehicleTypeIcon
        width={24}
        height={14}
        vehicleType={vehicle.vehicle_type}
      />
    ),
  };
}
