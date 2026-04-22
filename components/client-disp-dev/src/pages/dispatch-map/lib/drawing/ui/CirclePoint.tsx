import { type ThreeEvent, useFrame } from '@react-three/fiber';
import { useRef, useState } from 'react';
import type { Group } from 'three';

import { useCoordinatedDrag } from '../hooks/useCoordinatedDrag';
import { CIRCLE_SEGMENTS, HORIZONTAL_ROTATION, INNER_CIRCLE_Z_OFFSET } from '../model/constants';
import type { MoveScenePoint } from '../model/types';

/** Цвет точки в обычном состоянии. */
const DEFAULT_COLOR = '#FEFCF9';

/** Цвет точки при наведении. */
const HOVERED_COLOR = '#D15C29';

/** Цвет обводки точки. */
const DEFAULT_BORDER_COLOR = '#D15C29';

/** Толщина обводки. */
const DEFAULT_BORDER_WIDTH = 1;

/** Код для левой кнопки мыши. */
const LEFT_MOUSE_BUTTON = 0;

/**
 * Представляет свойства компонента {@link CirclePoint}.
 */
interface CirclePointProps {
  /** Уникальный идентификатор точки. */
  readonly id: string;
  /** Координата по оси X в сцене. */
  readonly x: number;
  /** Координата по оси Z в сцене. */
  readonly z: number;
  /** Высота точки (ось Y). */
  readonly y: number;
  /** Радиус внутреннего круга точки. */
  readonly size: number;
  /** Цвет точки в обычном состоянии. */
  readonly color?: string;
  /** Цвет точки при наведении. */
  readonly hoverColor?: string;
  /** Цвет обводки точки. */
  readonly borderColor?: string;
  /** Толщина обводки. */
  readonly borderWidth?: number;
  /** Вызывается при перемещении точки по плоскости. */
  readonly onMove?: MoveScenePoint;
  /** Вызывается при входе/выходе указателя из области точки. */
  readonly onHoverChange?: (id: string, isHovered: boolean) => void;
  /** Вызывается при клике по точке. */
  readonly onClick?: (id: string) => void;
  /** Вызывается при двойном клике по точке. */
  readonly onDoubleClick?: (id: string) => void;
  /** Вызывается при старте/окончании перетаскивания. */
  readonly onDragStateChange?: (isDragging: boolean) => void;
  /** При `true` — dragPositionRef обновляется каждый кадр, `onMove` вызывается только при отпускании. */
  readonly deferMove?: boolean;
}

/**
 * Перетаскиваемая точка на карте.
 */
export function CirclePoint({
  id,
  x,
  z,
  y,
  size,
  color = DEFAULT_COLOR,
  hoverColor = HOVERED_COLOR,
  borderColor = DEFAULT_BORDER_COLOR,
  borderWidth = DEFAULT_BORDER_WIDTH,
  onMove,
  onHoverChange,
  onClick,
  onDoubleClick,
  onDragStateChange,
  deferMove,
}: CirclePointProps) {
  const [isHovered, setIsHovered] = useState(false);
  const pointRef = useRef<Group>(null);

  const { startDrag, dragPositionRef } = useCoordinatedDrag({
    y,
    onMove,
    deferMove,
    onDragStart: () => onDragStateChange?.(true),
    onDragEnd: () => onDragStateChange?.(false),
  });

  useFrame(() => {
    if (!deferMove) return;
    const dragPosition = dragPositionRef.current;
    if (!dragPosition || dragPosition.id !== id || !pointRef.current) return;
    pointRef.current.position.x = dragPosition.x;
    pointRef.current.position.z = dragPosition.z;
  });

  const handlePointerOver = () => {
    setIsHovered(true);
    onHoverChange?.(id, true);
  };

  const handlePointerOut = () => {
    setIsHovered(false);
    onHoverChange?.(id, false);
  };

  const handlePointerDown = (event: ThreeEvent<PointerEvent>) => {
    if (!onMove || event.button !== LEFT_MOUSE_BUTTON) return;
    event.stopPropagation();
    startDrag(id);
  };

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    onClick?.(id);
  };

  const handleDoubleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    onDoubleClick?.(id);
  };

  return (
    <group
      ref={pointRef}
      position={[x, y, z]}
      rotation={HORIZONTAL_ROTATION}
      onPointerDown={handlePointerDown}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      onPointerOver={handlePointerOver}
      onPointerOut={handlePointerOut}
    >
      <mesh renderOrder={y}>
        <circleGeometry args={[size + borderWidth, CIRCLE_SEGMENTS]} />
        <meshBasicMaterial
          color={borderColor}
          transparent
          depthTest={false}
          depthWrite={false}
        />
      </mesh>
      <mesh
        position={[0, 0, INNER_CIRCLE_Z_OFFSET]}
        renderOrder={y + 1}
      >
        <circleGeometry args={[size, CIRCLE_SEGMENTS]} />
        <meshBasicMaterial
          color={isHovered ? hoverColor : color}
          transparent
          depthTest={false}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}
