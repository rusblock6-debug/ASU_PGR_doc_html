import { VehicleTypeIcon } from '@/entities/vehicle';

import { useConfirm } from '@/shared/lib/confirm';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { computeGroupCheck } from '../../../../lib/compute-group-check';
import { filterByName } from '../../../../lib/filter-by-name';
import { useExitGraphEdit } from '../../../../lib/hooks/useExitGraphEdit';
import { type MapVehicleItem, useMapVehicles } from '../../../../lib/hooks/useMapVehicles';
import { computeGroupVisibility } from '../../../../model/lib/compute-group-visibility';
import {
  selectSelectedVehicleHistoryIds,
  selectFormTarget,
  selectHasUnsavedChanges,
  selectHiddenVehicleIds,
  selectIsVisibleHistoryPlayer,
  selectMapFocusTarget,
  selectMapMode,
  selectSelectedHorizonId,
} from '../../../../model/selectors';
import { mapActions } from '../../../../model/slice';
import { Mode, TreeNode } from '../../../../model/types';
import { AddButton } from '../../AddButton';
import { CollapsibleSection } from '../../CollapsibleSection';
import { ObjectList } from '../ObjectList';

/** Конфигурация подгруппы машин для отображения в сайдбаре. */
const SUB_GROUPS = [
  { key: TreeNode.VEHICLES_PDM, label: 'ПДМ', group: 'pdm' },
  { key: TreeNode.VEHICLES_SHAS, label: 'ШАС', group: 'shas' },
] as const;

/**
 * Представляет свойства компонента {@link EquipmentSection}.
 */
interface EquipmentSectionProps {
  /** CSS-классы для кастомизации отдельных частей компонента. */
  readonly classNames?: Partial<Record<'root' | 'children', string>>;
  /** Строка поиска для фильтрации объектов по имени. */
  readonly searchQuery?: string;
}

/**
 * Секция «Оборудование предприятия» в сайдбаре карты — мобильное оборудование (ПДМ, ШАС).
 */
export function EquipmentSection({ classNames, searchQuery = '' }: EquipmentSectionProps) {
  const dispatch = useAppDispatch();
  const { groups, all, sorts } = useMapVehicles();
  const mapMode = useAppSelector(selectMapMode);
  const selectedHorizonId = useAppSelector(selectSelectedHorizonId);
  const hiddenVehicleIds = useAppSelector(selectHiddenVehicleIds);
  const selectedVehicleHistoryIds = useAppSelector(selectSelectedVehicleHistoryIds);
  const isVisibleHistoryPlayer = useAppSelector(selectIsVisibleHistoryPlayer);
  const hasUnsavedChanges = useAppSelector(selectHasUnsavedChanges);
  const formTarget = useAppSelector(selectFormTarget);
  const focusTarget = useAppSelector(selectMapFocusTarget);
  const confirm = useConfirm();
  const exitGraphEdit = useExitGraphEdit();

  const handleAdd = () => {
    dispatch(mapActions.setFormTarget({ entity: 'vehicle', id: null }));
    dispatch(mapActions.setPlacementPlaceToAdd(null));
  };

  const handleEdit = async (id: number) => {
    const canProceed = await exitGraphEdit(
      'Для редактирования объекта необходимо выйти из режима редактирования дорог. Несохранённые изменения будут потеряны.',
    );
    if (!canProceed) return;

    dispatch(mapActions.setFormTarget({ entity: 'vehicle', id }));
    dispatch(mapActions.setPlacementPlaceToAdd(null));
  };

  const handleAddClick = async () => {
    const canProceed = await exitGraphEdit(
      'Для создания нового объекта необходимо выйти из режима редактирования дорог. Несохранённые изменения будут потеряны.',
    );
    if (!canProceed) return;

    if (hasUnsavedChanges && (formTarget?.entity === 'place' || hasValue(formTarget?.id))) {
      const isConfirmed = await confirm({
        title: 'Вы действительно хотите создать новый объект?',
        message: `Текущие изменения будут утеряны.`,
        confirmText: 'Продолжить',
        cancelText: 'Отмена',
        size: 'md',
      });

      if (isConfirmed) {
        handleAdd();
      }
      return;
    }

    handleAdd();
  };

  const handleLocate = (id: number) => {
    const vehicle = all.find((item) => item.id === id);
    if (hasValue(vehicle?.horizon_id) && vehicle.horizon_id !== selectedHorizonId) {
      dispatch(mapActions.setSelectedHorizonId(vehicle.horizon_id));
    }

    dispatch(mapActions.setFocusTarget({ entity: 'vehicle', id }));
  };

  const handleToggleVisibility = (id: number) => {
    const isFocusedOnCurrentTarget = focusTarget?.entity === 'vehicle' && focusTarget?.id === id;
    if (isFocusedOnCurrentTarget) {
      dispatch(mapActions.setFocusTarget(null));
    }

    dispatch(mapActions.toggleVehicleVisibility(id));
  };

  const isSearchActive = searchQuery.trim().length > 0;

  const isHistoryMode = mapMode === Mode.HISTORY;

  const filtered = SUB_GROUPS.map(({ key, label, group }) => {
    const currentItems =
      isHistoryMode && isVisibleHistoryPlayer
        ? groups[group].filter((item) => selectedVehicleHistoryIds.includes(item.id))
        : groups[group];
    const items = filterByName(currentItems, searchQuery);
    const ids = items.map((item) => item.id);

    return {
      key,
      label,
      group,
      items: items.map(vehicleToObjectItem),
      ids,
      hasMatches: isSearchActive && items.length > 0,
    };
  });

  const allIds = filtered.flatMap((group) => group.ids);
  const totalCount = allIds.length;
  const hasAnyMatches = isSearchActive && totalCount > 0;

  return (
    <CollapsibleSection
      className={classNames?.root}
      groupKey={TreeNode.EQUIPMENT}
      label="Оборудование предприятия"
      count={totalCount}
      disabled={isSearchActive ? totalCount === 0 : undefined}
      forceExpanded={hasAnyMatches}
      visibility={computeGroupVisibility(allIds, hiddenVehicleIds)}
      onToggleVisibility={!isHistoryMode ? () => dispatch(mapActions.toggleVehiclesVisibility(allIds)) : undefined}
      leftSectionComponent={mapMode === Mode.EDIT && <AddButton onClick={handleAddClick} />}
      checked={computeGroupCheck(allIds, selectedVehicleHistoryIds)}
      onCheckChange={
        isHistoryMode && !isVisibleHistoryPlayer
          ? () => dispatch(mapActions.toggleVehicleHistoryIds(allIds))
          : undefined
      }
    >
      {(!isSearchActive || hasAnyMatches) && (
        <CollapsibleSection
          className={classNames?.children}
          groupKey={TreeNode.MOBILE_EQUIPMENT}
          label="Мобильное оборудование"
          count={totalCount}
          forceExpanded={hasAnyMatches}
          visibility={computeGroupVisibility(allIds, hiddenVehicleIds)}
          onToggleVisibility={!isHistoryMode ? () => dispatch(mapActions.toggleVehiclesVisibility(allIds)) : undefined}
          checked={computeGroupCheck(allIds, selectedVehicleHistoryIds)}
          onCheckChange={
            isHistoryMode && !isVisibleHistoryPlayer
              ? () => dispatch(mapActions.toggleVehicleHistoryIds(allIds))
              : undefined
          }
        >
          {filtered
            .filter((entry) => !isSearchActive || entry.items.length > 0)
            .map(({ key, label, group, items, ids, hasMatches }) => (
              <CollapsibleSection
                key={key}
                className={classNames?.children}
                groupKey={key}
                label={label}
                count={items.length}
                disabled={items.length === 0}
                forceExpanded={hasMatches}
                visibility={computeGroupVisibility(ids, hiddenVehicleIds)}
                onToggleVisibility={
                  !isHistoryMode ? () => dispatch(mapActions.toggleVehiclesVisibility(ids)) : undefined
                }
                checked={computeGroupCheck(ids, selectedVehicleHistoryIds)}
                onCheckChange={
                  isHistoryMode && !isVisibleHistoryPlayer
                    ? () => dispatch(mapActions.toggleVehicleHistoryIds(ids))
                    : undefined
                }
              >
                <ObjectList
                  items={items}
                  hiddenIds={hiddenVehicleIds}
                  sortState={sorts[group]}
                  onSortChange={(field) => dispatch(mapActions.toggleGroupSort({ entity: 'vehicle', group, field }))}
                  onLocate={handleLocate}
                  onToggleVisibility={handleToggleVisibility}
                  onEdit={handleEdit}
                />
              </CollapsibleSection>
            ))}
        </CollapsibleSection>
      )}
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
