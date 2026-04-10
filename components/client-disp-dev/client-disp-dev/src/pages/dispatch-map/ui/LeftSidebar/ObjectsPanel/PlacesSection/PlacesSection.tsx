import { PlaceTypeIcon } from '@/entities/place';

import { useConfirm } from '@/shared/lib/confirm';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import type { MapPlaceItem } from '../../../../lib/hooks/useMapPlaces';
import { useMapPlaces } from '../../../../lib/hooks/useMapPlaces';
import { computeGroupVisibility } from '../../../../model/lib/compute-group-visibility';
import {
  selectFormTarget,
  selectHasUnsavedChanges,
  selectHiddenPlaceIds,
  selectMapMode,
  selectSelectedHorizonId,
} from '../../../../model/selectors';
import { mapActions } from '../../../../model/slice';
import { Mode, TreeNode } from '../../../../model/types';
import { AddButton } from '../../AddButton';
import { CollapsibleSection } from '../../CollapsibleSection';
import { ObjectList } from '../ObjectList';

/**
 * Представляет свойства компонента {@link PlacesSection}.
 */
interface PlacesSectionProps {
  /** CSS-классы для кастомизации отдельных частей компонента. */
  readonly classNames?: Partial<Record<'root' | 'children', string>>;
}

/**
 * Секция «Места» в сайдбаре карты — перегрузка, погрузка, разгрузка, стоянки, транзит.
 */
export function PlacesSection({ classNames }: PlacesSectionProps) {
  const dispatch = useAppDispatch();
  const { groups, all, sorts } = useMapPlaces();
  const mapMode = useAppSelector(selectMapMode);
  const selectedHorizonId = useAppSelector(selectSelectedHorizonId);
  const hiddenPlaceIds = useAppSelector(selectHiddenPlaceIds);
  const isDirtyForm = useAppSelector(selectHasUnsavedChanges);
  const creatableEditableObject = useAppSelector(selectFormTarget);
  const confirm = useConfirm();

  const allIds = all.map((item) => item.id);
  const reloadIds = groups.reload.map((item) => item.id);
  const loadIds = groups.load.map((item) => item.id);
  const unloadIds = groups.unload.map((item) => item.id);
  const parkIds = groups.park.map((item) => item.id);
  const transitIds = groups.transit.map((item) => item.id);

  const reloadCount = groups.reload.length;
  const loadCount = groups.load.length;
  const unloadCount = groups.unload.length;
  const parkCount = groups.park.length;
  const transitCount = groups.transit.length;

  const addPlace = () => {
    dispatch(mapActions.setFormTarget({ entity: 'place', id: null }));
    dispatch(mapActions.setPlacementPlaceToAdd(null));
  };

  const handleEdit = (id: number) => {
    dispatch(mapActions.setFormTarget({ entity: 'place', id }));
    dispatch(mapActions.setPlacementPlaceToAdd(null));
  };

  const handleAddClick = async () => {
    if (isDirtyForm && (creatableEditableObject?.entity === 'vehicle' || hasValue(creatableEditableObject?.id))) {
      const isConfirmed = await confirm({
        title: 'Вы действительно хотите создать новое место?',
        message: `Текущие изменения будут утеряны.`,
        confirmText: 'Продолжить',
        cancelText: 'Отмена',
        size: 'md',
      });

      if (isConfirmed) {
        addPlace();
      }

      return;
    }

    addPlace();
  };

  const handleLocate = (id: number) => {
    const place = all.find((item) => item.id === id);
    if (hasValue(place?.horizon_id) && place.horizon_id !== selectedHorizonId) {
      dispatch(mapActions.setSelectedHorizonId(place.horizon_id));
    }

    dispatch(mapActions.setFocusTarget({ entity: 'place', id }));
  };

  const handleToggleVisibility = (id: number) => dispatch(mapActions.togglePlaceVisibility(id));

  return (
    <CollapsibleSection
      className={classNames?.root}
      groupKey={TreeNode.PLACES}
      label="Места"
      count={all.length}
      visibility={computeGroupVisibility(allIds, hiddenPlaceIds)}
      onToggleVisibility={() => dispatch(mapActions.togglePlacesVisibility(allIds))}
      leftSectionComponent={mapMode === Mode.EDIT && <AddButton onClick={handleAddClick} />}
    >
      <CollapsibleSection
        className={classNames?.children}
        groupKey={TreeNode.PLACES_RELOAD}
        label="Места перегрузки"
        count={reloadCount}
        disabled={reloadCount === 0}
        visibility={computeGroupVisibility(reloadIds, hiddenPlaceIds)}
        onToggleVisibility={() => dispatch(mapActions.togglePlacesVisibility(reloadIds))}
      >
        <ObjectList
          items={groups.reload.map(placeToObjectItem)}
          hiddenIds={hiddenPlaceIds}
          sortState={sorts.reload}
          onSortChange={(field) => dispatch(mapActions.toggleGroupSort({ entity: 'place', group: 'reload', field }))}
          onLocate={handleLocate}
          onToggleVisibility={handleToggleVisibility}
          onEdit={handleEdit}
        />
      </CollapsibleSection>

      <CollapsibleSection
        className={classNames?.children}
        groupKey={TreeNode.PLACES_LOAD}
        label="Места погрузки"
        count={loadCount}
        disabled={loadCount === 0}
        visibility={computeGroupVisibility(loadIds, hiddenPlaceIds)}
        onToggleVisibility={() => dispatch(mapActions.togglePlacesVisibility(loadIds))}
      >
        <ObjectList
          items={groups.load.map(placeToObjectItem)}
          hiddenIds={hiddenPlaceIds}
          sortState={sorts.load}
          onSortChange={(field) => dispatch(mapActions.toggleGroupSort({ entity: 'place', group: 'load', field }))}
          onLocate={handleLocate}
          onToggleVisibility={handleToggleVisibility}
          onEdit={handleEdit}
        />
      </CollapsibleSection>

      <CollapsibleSection
        className={classNames?.children}
        groupKey={TreeNode.PLACES_UNLOAD}
        label="Места разгрузки"
        count={unloadCount}
        disabled={unloadCount === 0}
        visibility={computeGroupVisibility(unloadIds, hiddenPlaceIds)}
        onToggleVisibility={() => dispatch(mapActions.togglePlacesVisibility(unloadIds))}
      >
        <ObjectList
          items={groups.unload.map(placeToObjectItem)}
          hiddenIds={hiddenPlaceIds}
          sortState={sorts.unload}
          onSortChange={(field) => dispatch(mapActions.toggleGroupSort({ entity: 'place', group: 'unload', field }))}
          onLocate={handleLocate}
          onToggleVisibility={handleToggleVisibility}
          onEdit={handleEdit}
        />
      </CollapsibleSection>

      <CollapsibleSection
        className={classNames?.children}
        groupKey={TreeNode.PLACES_PARK}
        label="Места стоянок"
        count={parkCount}
        disabled={parkCount === 0}
        visibility={computeGroupVisibility(parkIds, hiddenPlaceIds)}
        onToggleVisibility={() => dispatch(mapActions.togglePlacesVisibility(parkIds))}
      >
        <ObjectList
          items={groups.park.map(placeToObjectItem)}
          hiddenIds={hiddenPlaceIds}
          sortState={sorts.park}
          onSortChange={(field) => dispatch(mapActions.toggleGroupSort({ entity: 'place', group: 'park', field }))}
          onLocate={handleLocate}
          onToggleVisibility={handleToggleVisibility}
          onEdit={handleEdit}
        />
      </CollapsibleSection>

      <CollapsibleSection
        className={classNames?.children}
        groupKey={TreeNode.PLACES_TRANSIT}
        label="Транзитные места"
        count={transitCount}
        disabled={transitCount === 0}
        visibility={computeGroupVisibility(transitIds, hiddenPlaceIds)}
        onToggleVisibility={() => dispatch(mapActions.togglePlacesVisibility(transitIds))}
      >
        <ObjectList
          items={groups.transit.map(placeToObjectItem)}
          hiddenIds={hiddenPlaceIds}
          sortState={sorts.transit}
          onSortChange={(field) => dispatch(mapActions.toggleGroupSort({ entity: 'place', group: 'transit', field }))}
          onLocate={handleLocate}
          onToggleVisibility={handleToggleVisibility}
          onEdit={handleEdit}
        />
      </CollapsibleSection>
    </CollapsibleSection>
  );
}

/**
 * Преобразует места в элемент списка объектов.
 */
function placeToObjectItem(place: MapPlaceItem) {
  return {
    id: place.id,
    name: place.name,
    horizon: place.horizon_name,
    stock: place.stock,
    icon: (
      <PlaceTypeIcon
        width={24}
        height={14}
        placeType={place.type}
      />
    ),
  };
}
