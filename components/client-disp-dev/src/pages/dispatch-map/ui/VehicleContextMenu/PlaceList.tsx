import type { Horizon } from '@/shared/api/endpoints/horizons';
import type { Place } from '@/shared/api/endpoints/places';
import { hasValue } from '@/shared/lib/has-value';
import { CategorizedList } from '@/shared/ui/CategorizedList';

import styles from './PlaceList.module.css';

/** Представляет свойства компонента списка мест с группировкой по горизонтам. */
interface PlaceListProps {
  /** Возвращает список мест. */
  readonly places: readonly Place[];
  /** Возвращает список горизонтов. */
  readonly horizons: readonly Horizon[];
  /** Возвращает делегат, вызываемый при выборе места. */
  readonly onSelect?: (place: Place) => void;
}

/**
 * Список мест, сгруппированный по горизонтам.
 * Места без привязки к горизонту не отображаются.
 */
export function PlaceList({ places, horizons, onSelect }: PlaceListProps) {
  const horizonHeightMap = new Map(horizons.map((horizon) => [horizon.id, horizon.height]));
  const placesWithHorizon = [...places]
    .filter((place) => hasValue(place.horizon_id))
    .sort((a, b) => (horizonHeightMap.get(b.horizon_id ?? 0) ?? 0) - (horizonHeightMap.get(a.horizon_id ?? 0) ?? 0));

  return (
    <CategorizedList
      searchable
      items={placesWithHorizon}
      onSelect={onSelect}
      getItemKey={(place) => place.id}
      getCategory={(place) => ({
        key: String(place.horizon_id),
        label: hasValue(place.horizon_id) ? `Горизонт: ${horizonHeightMap.get(place.horizon_id)} м` : '',
      })}
      getSearchText={(place) => place.name}
      renderItem={(place) => <p className={styles.text}>{place.name}</p>}
    />
  );
}
