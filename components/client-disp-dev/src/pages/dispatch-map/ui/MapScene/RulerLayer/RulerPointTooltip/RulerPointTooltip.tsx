import type { Vector3Tuple } from 'three';

import CrossIcon from '@/shared/assets/icons/ic-cross.svg?react';
import TrashIcon from '@/shared/assets/icons/ic-trash.svg?react';

import { SceneTooltip, TooltipButton } from '../../../../lib/drawing';

import styles from './RulerPointTooltip.module.css';

/**
 * Представляет свойства компонента {@link RulerPointTooltip}.
 */
interface RulerPointTooltipProps {
  /** Позиция в сцене [x, y, z]. */
  readonly position: Vector3Tuple;
  /** Текст расстояния (например, "123 м"), null для первой точки. */
  readonly distance: string | null;
  /** Удалить вершину. */
  readonly onDelete: () => void;
  /** Закрыть тултип. */
  readonly onClose: () => void;
}

/**
 * Интерактивный попап над вершиной полилинии.
 *
 * Показывает кумулятивное расстояние, кнопку удаления (корзина)
 * и кнопку закрытия (крестик).
 */
export function RulerPointTooltip({ position, distance, onDelete, onClose }: RulerPointTooltipProps) {
  return (
    <SceneTooltip position={position}>
      {distance && <span className={styles.distance}>{distance}</span>}

      <TooltipButton
        tooltip="Удалить точку (двойной клик)"
        onClick={onDelete}
      >
        <TrashIcon />
      </TooltipButton>

      <TooltipButton
        tooltip="Закрыть"
        onClick={onClose}
      >
        <CrossIcon />
      </TooltipButton>
    </SceneTooltip>
  );
}
