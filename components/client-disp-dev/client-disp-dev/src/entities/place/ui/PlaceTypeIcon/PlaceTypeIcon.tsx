import type { SVGProps } from 'react';

import type { PlaceType } from '@/shared/api/endpoints/places';

import UnknowPlaceIcon from '../../assets/icons/ic-unknow.svg?react';
import { getPlaceTypeIcon } from '../../model/constants';

/**
 * Представляет свойства для компонента {@link PlaceTypeIcon}.
 * Наследуются от стандартных SVG-пропсов, плюс обязательный `placeType`.
 */
interface PlaceTypeIconProps extends SVGProps<SVGSVGElement> {
  /** Тип транспортного средства. */
  readonly placeType?: PlaceType | null;
}

/**
 * Представляет компонент иконки в соответствии с типом техники.
 * Если для переданного `placeType` иконки нет, ничего не отображает.
 */
export function PlaceTypeIcon({ placeType, ...props }: PlaceTypeIconProps) {
  const Icon = placeType ? getPlaceTypeIcon(placeType) : UnknowPlaceIcon;
  return <Icon {...props} />;
}
