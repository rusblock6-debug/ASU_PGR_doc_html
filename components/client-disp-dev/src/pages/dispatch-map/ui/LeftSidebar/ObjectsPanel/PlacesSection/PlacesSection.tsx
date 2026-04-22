import { PlaceTypeIcon } from '@/entities/place';

import { useConfirm } from '@/shared/lib/confirm';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { filterByName } from '../../../../lib/filter-by-name';
import { useExitGraphEdit } from '../../../../lib/hooks/useExitGraphEdit';
import type { MapPlaceItem } from '../../../../lib/hooks/useMapPlaces';
import { useMapPlaces } from '../../../../lib/hooks/useMapPlaces';
import { computeGroupVisibility } from '../../../../model/lib/compute-group-visibility';
import {
  selectFormTarget,
  selectHasUnsavedChanges,
  selectHiddenPlaceIds,
  selectMapFocusTarget,
  selectMapMode,
  selectSelectedHorizonId,
} from '../../../../model/selectors';
import { mapActions } from '../../../../model/slice';
import { Mode, TreeNode } from '../../../../model/types';
import { AddButton } from '../../AddButton';
import { CollapsibleSection } from '../../CollapsibleSection';
import { ObjectList } from '../ObjectList';

/** Конфигурация подгруппы мест для отображения в сайдбаре. */
const SUB_GROUPS = [
  { key: TreeNode.PLACES_RELOAD, label: 'Места перегрузки', group: 'reload' },
  { key: TreeNode.PLACES_LOAD, label: 'Места погрузки', group: 'load' },
  { key: TreeNode.PLACES_UNLOAD, label: 'Места разгрузки', group: 'unload' },
  { key: TreeNode.PLACES_PARK, label: 'Места стоянок', group: 'park' },
  { key: TreeNode.PLACES_TRANSIT, label: 'Транзитные места', group: 'transit' },
] as const;

/**
 * Представляет свойства компонента {@link PlacesSection}.
 */
interface PlacesSectionProps {
  /** CSS-классы для кастомизации отдельных частей компонента. */
  readonly classNames?: Partial<Record<'root' | 'children', string>>;
  /** Строка поиска для фильтрации объектов по имени. */
  readonly searchQuery?: string;
}

/**
 * Секция «Места» в сайдбаре карты — перегрузка, погрузка, разгрузка, стоянки, транзит.
 */
export function PlacesSection({ classNames, searchQuery = '' }: PlacesSectionProps) {
  const dispatch = useAppDispatch();
  const { groups, all, sorts } = useMapPlaces();
  const mapMode = useAppSelector(selectMapMode);
  const selectedHorizonId = useAppSelector(selectSelectedHorizonId);
  const hiddenPlaceIds = useAppSelector(selectHiddenPlaceIds);
  const hasUnsavedChanges = useAppSelector(selectHasUnsavedChanges);
  const formTarget = useAppSelector(selectFormTarget);
  const focusTarget = useAppSelector(selectMapFocusTarget);
  const confirm = useConfirm();
  const exitGraphEdit = useExitGraphEdit();

  const addPlace = () => {
    dispatch(mapActions.setFormTarget({ entity: 'place', id: null }));
    dispatch(mapActions.setPlacementPlaceToAdd(null));
  };

  const handleEdit = async (id: number) => {
    const canProceed = await exitGraphEdit(
      'Для редактирования места необходимо выйти из режима редактирования дорог. Несохранённые изменения будут потеряны.',
    );
    if (!canProceed) return;

    dispatch(mapActions.setFormTarget({ entity: 'place', id }));
    dispatch(mapActions.setPlacementPlaceToAdd(null));
  };

  const handleAddClick = async () => {
    const canProceed = await exitGraphEdit(
      'Для создания нового места необходимо выйти из режима редактирования дорог. Несохранённые изменения будут потеряны.',
    );
    if (!canProceed) return;

    if (hasUnsavedChanges && (formTarget?.entity === 'vehicle' || hasValue(formTarget?.id))) {
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

  const handleToggleVisibility = (id: number) => {
    const isFocusedOnCurrentTarget = focusTarget?.entity === 'place' && focusTarget?.id === id;
    if (isFocusedOnCurrentTarget) {
      dispatch(mapActions.setFocusTarget(null));
    }

    dispatch(mapActions.togglePlaceVisibility(id));
  };

  const isSearchActive = searchQuery.trim().length > 0;

  const filtered = SUB_GROUPS.map(({ key, label, group }) => {
    const items = filterByName(groups[group], searchQuery);
    const ids = items.map((item) => item.id);

    return {
      key,
      label,
      group,
      items: items.map(placeToObjectItem),
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
      groupKey={TreeNode.PLACES}
      label="Места"
      count={totalCount}
      disabled={isSearchActive ? totalCount === 0 : undefined}
      forceExpanded={hasAnyMatches}
      visibility={computeGroupVisibility(allIds, hiddenPlaceIds)}
      onToggleVisibility={() => dispatch(mapActions.togglePlacesVisibility(allIds))}
      leftSectionComponent={mapMode === Mode.EDIT && <AddButton onClick={handleAddClick} />}
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
            visibility={computeGroupVisibility(ids, hiddenPlaceIds)}
            onToggleVisibility={() => dispatch(mapActions.togglePlacesVisibility(ids))}
          >
            <ObjectList
              items={items}
              hiddenIds={hiddenPlaceIds}
              sortState={sorts[group]}
              onSortChange={(field) => dispatch(mapActions.toggleGroupSort({ entity: 'place', group, field }))}
              onLocate={handleLocate}
              onToggleVisibility={handleToggleVisibility}
              onEdit={handleEdit}
            />
          </CollapsibleSection>
        ))}
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
