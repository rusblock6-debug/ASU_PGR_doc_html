import type { PlaceType } from '@/shared/api/endpoints/places';
import { assertNever } from '@/shared/lib/assert-never';

import loadImg from '../assets/icons/ic-load-orange.svg';
import LoadPlaceIcon from '../assets/icons/ic-load.svg?react';
import parkImg from '../assets/icons/ic-park-orange.svg';
import ParkPlaceIcon from '../assets/icons/ic-park.svg?react';
import reloadImg from '../assets/icons/ic-reload-orange.svg';
import ReloadPlaceIcon from '../assets/icons/ic-reload.svg?react';
import transitImg from '../assets/icons/ic-transit-orange.svg';
import TransitPlaceIcon from '../assets/icons/ic-transit.svg?react';
import unloadImg from '../assets/icons/ic-unload-orange.svg';
import UnloadPlaceIcon from '../assets/icons/ic-unload.svg?react';

/**
 * Список типов мест.
 * Используется для инициализации zod-схемы валидации.
 */
export const PLACE_TYPES = ['load', 'unload', 'reload', 'transit', 'park'] as const satisfies readonly PlaceType[];

/** Маппинг типов оборудования на их отображаемые названия. */
export const PlaceTypeLabels = {
  load: 'Место погрузки',
  unload: 'Место разгрузки',
  reload: 'Место перегрузки',
  transit: 'Транзитное место',
  park: 'Место стоянки',
} as const satisfies Record<PlaceType, string>;

/** Опции для селекта типа места. */
export const placeTypeOptions = Object.entries(PlaceTypeLabels).map(([value, label]) => ({ value, label }));

/**
 * Возвращает иконку типа места.
 *
 * @param placeType тип места.
 */
export function getPlaceTypeIcon(placeType: PlaceType) {
  switch (placeType) {
    case 'load':
      return LoadPlaceIcon;
    case 'unload':
      return UnloadPlaceIcon;
    case 'park':
      return ParkPlaceIcon;
    case 'transit':
      return TransitPlaceIcon;
    case 'reload':
      return ReloadPlaceIcon;
    default:
      assertNever(placeType);
  }
}

/**
 * Возвращает иконку типа места с заданным цветом (оранжевый).
 * Используется для размещения в img теге.
 *
 * @param placeType тип места.
 */
export function getPlaceTypeOrangeIcon(placeType: PlaceType) {
  switch (placeType) {
    case 'load':
      return loadImg;
    case 'unload':
      return unloadImg;
    case 'park':
      return parkImg;
    case 'transit':
      return transitImg;
    case 'reload':
      return reloadImg;
    default:
      assertNever(placeType);
  }
}
