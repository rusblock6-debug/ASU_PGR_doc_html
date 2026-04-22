import type { Vector3Tuple } from 'three';

import ConfirmIcon from '@/shared/assets/icons/ic-confirm.svg?react';
import CrossIcon from '@/shared/assets/icons/ic-cross.svg?react';
import PlusIcon from '@/shared/assets/icons/ic-plus.svg?react';
import TrashIcon from '@/shared/assets/icons/ic-trash.svg?react';

import { SceneTooltip, TooltipButton } from '../../../lib/drawing';

/**
 * Представляет свойства компонента {@link NodeTooltip}.
 */
interface NodeTooltipProps {
  /** Позиция в сцене [x, y, z]. */
  readonly position: Vector3Tuple;
  /** Является ли этот узел источником текущего рисования ребра. */
  readonly isDrawingSource: boolean;
  /** Добавить ребро от этого узла / завершить добавление. */
  readonly onAddEdge: () => void;
  /** Удалить узел. */
  readonly onDelete: () => void;
  /** Закрыть тултип. */
  readonly onClose: () => void;
}

/**
 * Интерактивный попап над узлом графа.
 */
export function NodeTooltip({ position, isDrawingSource, onAddEdge, onDelete, onClose }: NodeTooltipProps) {
  return (
    <SceneTooltip position={position}>
      <TooltipButton
        tooltip={isDrawingSource ? 'Завершить добавление' : 'Добавить дорогу'}
        onClick={onAddEdge}
      >
        {isDrawingSource ? <ConfirmIcon /> : <PlusIcon />}
      </TooltipButton>

      <TooltipButton
        tooltip="Удалить узел (двойной клик)"
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
