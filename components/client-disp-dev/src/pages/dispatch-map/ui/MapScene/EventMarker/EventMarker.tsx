import type { MouseEvent } from 'react';
import { useState } from 'react';
import type { Vector3Tuple } from 'three';

import { cn } from '@/shared/lib/classnames-utils';

import { MAP_SCENE } from '../../../config/map-scene';
import { ProximityHtml } from '../ProximityHtml';

import styles from './EventMarker.module.css';

/**
 * Представляет свойства компонента {@link EventMarker}.
 */
interface VehicleMarkerProps {
  /** Идентификатор транспорта. */
  readonly id: number;
  /** Временная метка. */
  readonly timestamp: string;
  /** Позиция в 3D-сцене [x, y, z]. */
  readonly position: Vector3Tuple;
  /** Транспорт был выбран в сайдбаре. */
  readonly isSelected?: boolean;
  /** Колбэк при наведении курсора. Передаёт id транспорта или null. */
  readonly onHover: (vehicleId: number | null, timestamp: string | null) => void;
  /** Колбэк при клике ЛКМ на маркере. */
  readonly onClick?: (vehicleId: number, event: MouseEvent) => void;
  /** Колбэк при клике ПКМ на маркере. */
  readonly onContextMenu?: (vehicleId: number, event: MouseEvent) => void;
}

/**
 * Маркер следа транспорта на карте с иконкой и подписью.
 */
export function EventMarker({
  id,
  timestamp,
  position,
  isSelected = false,
  onHover,
  onClick,
  onContextMenu,
}: VehicleMarkerProps) {
  const [isHovered, setIsHovered] = useState(false);

  const handleOver = () => {
    setIsHovered(true);
    onHover(id, timestamp);
  };

  const handleOut = () => {
    setIsHovered(false);
    onHover(null, null);
  };

  const handleClick = (e: MouseEvent) => {
    e.preventDefault();
    onClick?.(id, e);
  };

  const handleContextMenu = (e: MouseEvent) => {
    e.preventDefault();
    onContextMenu?.(id, e);
  };

  return (
    <group position={position}>
      <ProximityHtml
        center
        threshold={MAP_SCENE.PROXIMITY_THRESHOLD}
        minScale={MAP_SCENE.MIN_PROXIMITY_SCALE}
        baseScale={MAP_SCENE.BASE_HTML_SCALE}
        renderOrder={MAP_SCENE.PLACES_Y}
        zIndexRange={[MAP_SCENE.PLACES_Y, MAP_SCENE.PLACES_Y]}
      >
        <div
          className={cn(styles.event_marker, {
            [styles.hovered]: isHovered,
            [styles.selected]: isSelected,
          })}
          onPointerOver={handleOver}
          onPointerOut={handleOut}
          onClick={handleClick}
          onContextMenu={handleContextMenu}
        />
      </ProximityHtml>
    </group>
  );
}
