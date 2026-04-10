import type { CSSProperties } from 'react';
import { useState } from 'react';
import type { Vector3Tuple } from 'three';

import { VehicleTypeIcon } from '@/entities/vehicle';

import type { VehicleType } from '@/shared/api/endpoints/vehicles';
import { cn } from '@/shared/lib/classnames-utils';

import { MAP_SCENE } from '../../../config/map-scene';
import { ProximityHtml } from '../ProximityHtml';

import styles from './VehicleMarker.module.css';

/**
 * Представляет свойства компонента {@link VehicleMarker}.
 */
interface VehicleMarkerProps {
  /** Идентификатор транспорта. */
  readonly id: number;
  /** Название транспорта. */
  readonly name: string;
  /** Тип транспорта. */
  readonly vehicleType: VehicleType;
  /** Позиция в 3D-сцене [x, y, z]. */
  readonly position: Vector3Tuple;
  /** Транспорт был выбран в сайдбаре. */
  readonly isSelected?: boolean;
  /** Цвет статуса транспорта (hex/rgb). */
  readonly color?: string;
  /** Интерактивен ли маркер (hover). */
  readonly interactive?: boolean;
  /** Колбэк при наведении курсора. Передаёт id транспорта или null. */
  readonly onHover: (vehicleId: number | null) => void;
}

/**
 * Маркер транспорта на карте с иконкой и подписью.
 */
export function VehicleMarker({
  id,
  name,
  vehicleType,
  position,
  isSelected = false,
  color,
  interactive = true,
  onHover,
}: VehicleMarkerProps) {
  const [isHovered, setIsHovered] = useState(false);

  const handleOver = () => {
    setIsHovered(true);
    onHover(id);
  };

  const handleOut = () => {
    setIsHovered(false);
    onHover(null);
  };

  return (
    <group position={position}>
      <ProximityHtml
        center
        threshold={MAP_SCENE.PROXIMITY_THRESHOLD}
        minScale={MAP_SCENE.MIN_PROXIMITY_SCALE}
        baseScale={MAP_SCENE.BASE_HTML_SCALE}
        renderOrder={MAP_SCENE.VEHICLES_Y}
        zIndexRange={[MAP_SCENE.VEHICLES_Y, MAP_SCENE.VEHICLES_Y]}
      >
        <div
          className={cn(styles.vehicle_marker, {
            [styles.hovered]: isHovered,
            [styles.selected]: isSelected,
            [styles.non_interactive]: !interactive,
          })}
          style={color ? ({ '--marker-color': color } as CSSProperties) : undefined}
          onPointerOver={handleOver}
          onPointerOut={handleOut}
        >
          <VehicleTypeIcon
            className={cn(styles.vehicle_icon, styles.vehicle_wrapper)}
            vehicleType={vehicleType}
            width={58}
            height={20}
          />
          <div className={cn(styles.vehicle_label, styles.vehicle_wrapper, 'truncate')}>{name}</div>
        </div>
      </ProximityHtml>
    </group>
  );
}
