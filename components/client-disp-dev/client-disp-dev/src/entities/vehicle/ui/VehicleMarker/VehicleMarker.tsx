import { type CSSProperties, type ForwardedRef, forwardRef } from 'react';

import type { VehicleType } from '@/shared/api/endpoints/vehicles';
import { assertNever } from '@/shared/lib/assert-never';
import { cn } from '@/shared/lib/classnames-utils';

import { VehicleTypeIcon } from '../VehicleTypeIcon';

import styles from './VehicleMarker.module.css';

/**
 * Представляет свойства компонента маркера оборудования.
 */
interface VehicleMarkerProps {
  /** Возвращает тип оборудования. */
  readonly vehicleType: VehicleType;
  /** Возвращает наименование. */
  readonly name: string;
  /** Возвращает цвет. */
  readonly color?: string;
  /** Возвращает размер. */
  readonly size?: 's' | 'm';
  /** Возвращает признак выбранной иконки. */
  readonly selected?: boolean;
  /** Возвращает признак наведения мыши. */
  readonly hovered?: boolean;
  /** Возвращает признак интерактивности. */
  readonly interactive?: boolean;
  /** Возвращает признак отображения в горизонтальном варианте. */
  readonly horizontal?: boolean;
  /** Возвращает признак отображения отраженной иконки. */
  readonly mirrored?: boolean;
  /** Возвращает признак нормального отображения наименование (не absolute)я. */
  readonly isNormalLabelPosition?: boolean;
  /** Возвращает делегат, вызываемый при клике ЛКМ. */
  readonly onClick?: () => void;
  /** Возвращает делегат, вызываемый при клике ПКМ. */
  readonly onContextMenu?: () => void;
  /** Возвращает прозрачность иконки. */
  readonly iconOpacity?: number;
}

/**
 * Представляет компонент маркера оборудования.
 */
export function VehicleMarkerComponent(
  {
    vehicleType,
    name,
    color,
    size = 'm',
    selected = false,
    hovered = false,
    interactive = true,
    horizontal = false,
    mirrored = false,
    isNormalLabelPosition = false,
    onClick,
    onContextMenu,
    iconOpacity,
  }: VehicleMarkerProps,
  ref: ForwardedRef<HTMLDivElement>,
) {
  return (
    <div
      ref={ref}
      className={cn(styles.vehicle_marker, {
        [styles.hovered]: hovered,
        [styles.selected]: selected,
        [styles.non_interactive]: !interactive,
        [styles.normal_label_position]: isNormalLabelPosition,
        [styles.horizontal]: horizontal,
        [styles.vertical]: !horizontal,
      })}
      style={color ? ({ '--marker-color': color } as CSSProperties) : undefined}
      onClick={onClick}
      onContextMenu={(e) => {
        e.preventDefault();
        onContextMenu?.();
      }}
    >
      <VehicleTypeIcon
        className={cn(styles.vehicle_icon, styles.vehicle_wrapper, { [styles.mirrored]: mirrored })}
        style={{ opacity: iconOpacity }}
        vehicleType={vehicleType}
        {...getIconSize(size)}
      />
      <div
        className={cn(styles.vehicle_label, styles.vehicle_wrapper, 'truncate', {
          [styles.vertical]: !horizontal,
          [styles.absolute]: !isNormalLabelPosition,
        })}
      >
        {name}
      </div>
    </div>
  );
}

export const VehicleMarker = forwardRef(VehicleMarkerComponent);

/**
 * Возвращает размеры иконки маркера оборудования.
 *
 * @param size размер маркера.
 */
function getIconSize(size: VehicleMarkerProps['size'] = 'm') {
  switch (size) {
    case 'm':
      return {
        width: 58,
        height: 20,
      };
    case 's':
      return {
        width: 36,
        height: 16,
      };
    default:
      return assertNever(size);
  }
}
