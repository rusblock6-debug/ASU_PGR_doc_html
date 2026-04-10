import { type ForwardedRef, forwardRef, type ReactNode, useState } from 'react';
import type { Group, Vector3Tuple } from 'three';

import { getPlaceTypeOrangeIcon } from '@/entities/place';

import type { PlaceType } from '@/shared/api/endpoints/places';
import { cn } from '@/shared/lib/classnames-utils';
import { hasValue } from '@/shared/lib/has-value';

import { MAP_SCENE } from '../../../config/map-scene';
import { ProximityHtml } from '../ProximityHtml';

import styles from './PlaceMarker.module.css';

/**
 * Представляет свойства компонента {@link PlaceMarker}.
 */
interface MapPlaceProps {
  /** Идентификатор места. */
  readonly id: number | null;
  /** Название места. */
  readonly name?: string;
  /** Тип места (погрузка, разгрузка и т.д.). */
  readonly placeType: PlaceType;
  /** Позиция в 3D-сцене [x, y, z]. */
  readonly position: Vector3Tuple;
  /** Место было выбрано в сайдбаре. */
  readonly isSelected?: boolean;
  /** Интерактивен ли маркер (hover). */
  readonly interactive?: boolean;
  /** Колбэк при наведении курсора. Передаёт id места или null. */
  readonly onHover?: (placeId: number | null) => void;
  /** Режим предварительного показа. */
  readonly isPreview?: boolean;
  /** Подсказка. */
  readonly hint?: ReactNode;
}

/**
 * Маркер места на карте с иконкой и подписью.
 */
function PlaceMarkerComponent(
  {
    id,
    name,
    placeType,
    position,
    isSelected = false,
    interactive = true,
    onHover,
    isPreview = false,
    hint,
  }: MapPlaceProps,
  ref: ForwardedRef<Group>,
) {
  const [isHovered, setIsHovered] = useState(false);
  const iconUrl = getPlaceTypeOrangeIcon(placeType);

  const handleOver = () => {
    setIsHovered(true);
    onHover?.(id);
  };

  const handleOut = () => {
    setIsHovered(false);
    onHover?.(null);
  };

  return (
    <group
      ref={ref}
      position={position}
    >
      <ProximityHtml
        center
        threshold={MAP_SCENE.PROXIMITY_THRESHOLD}
        minScale={MAP_SCENE.MIN_PROXIMITY_SCALE}
        baseScale={MAP_SCENE.BASE_HTML_SCALE}
        renderOrder={MAP_SCENE.PLACES_Y}
        zIndexRange={[MAP_SCENE.PLACES_Y, MAP_SCENE.PLACES_Y]}
        style={{ pointerEvents: isPreview ? 'none' : 'auto' }}
      >
        <div
          className={cn(styles.place_marker, {
            [styles.hovered]: isHovered,
            [styles.selected]: isSelected,
            [styles.non_interactive]: !interactive,
          })}
          onPointerOver={handleOver}
          onPointerOut={handleOut}
        >
          <img
            src={iconUrl}
            alt={name}
            draggable={false}
            width={24}
            height={24}
            className={styles.place_icon}
          />
          {hasValue(name) && <div className={cn(styles.place_label, styles.place, 'truncate')}>{name}</div>}
        </div>
        {hint ? <div className={cn(styles.place_label, styles.hint)}>{hint}</div> : null}
      </ProximityHtml>
    </group>
  );
}

export const PlaceMarker = forwardRef(PlaceMarkerComponent);
