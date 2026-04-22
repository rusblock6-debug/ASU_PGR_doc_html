import type { PointerEvent } from 'react';
import type { Vector3Tuple } from 'three';

import ConfirmIcon from '@/shared/assets/icons/ic-confirm.svg?react';
import CrossIcon from '@/shared/assets/icons/ic-cross.svg?react';
import TrashIcon from '@/shared/assets/icons/ic-trash.svg?react';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { Select } from '@/shared/ui/Select';

import { BridgedSceneTooltip, TooltipButton } from '../../../lib/drawing';
import { useMapPlaces } from '../../../lib/hooks/useMapPlaces';
import type { GraphElementTypeValue } from '../../../model/graph';
import { graphEditActions, GraphElementType, selectLadderSource, selectLadderTarget } from '../../../model/graph';
import { selectSelectedHorizonId } from '../../../model/selectors';

import styles from './LadderNodeTooltip.module.css';

/**
 * Представляет свойства компонента {@link LadderNodeTooltip}.
 */
interface LadderNodeTooltipProps {
  /** Серверный идентификатор узла. */
  readonly nodeId: number;
  /** Позиция в сцене [x, y, z]. */
  readonly position: Vector3Tuple;
  /** Тип узла графа. */
  readonly nodeType: GraphElementTypeValue;
  /** Идентификатор горизонта, к которому привязан узел (целевой горизонт переезда). */
  readonly nodeHorizonId: number | null;
  /** Удалить переезд. */
  readonly onDeleteLadder: () => void;
  /** Закрыть тултип. */
  readonly onClose: () => void;
  /** Выбрать горизонт для переезда. */
  readonly onSelectHorizon: (horizonId: number) => void;
}

/**
 * Попап над узлом графа в режиме редактирования переездов.
 */
export function LadderNodeTooltip({
  nodeId,
  position,
  nodeType,
  nodeHorizonId,
  onDeleteLadder,
  onClose,
  onSelectHorizon,
}: LadderNodeTooltipProps) {
  const dispatch = useAppDispatch();

  const horizonId = useAppSelector(selectSelectedHorizonId);
  const ladderSource = useAppSelector(selectLadderSource);
  const ladderTarget = useAppSelector(selectLadderTarget);

  const { horizons } = useMapPlaces();

  const isSelectingTarget = ladderSource !== null && horizonId !== ladderSource.horizonId;
  const isTargetConfirmed = isSelectingTarget && ladderTarget !== null && nodeId === ladderTarget.nodeId;

  const currentHorizon = horizons.find((horizon) => horizon.id === horizonId);
  const linkedHorizon =
    nodeType === GraphElementType.LADDER ? horizons.find((horizon) => horizon.id === nodeHorizonId) : undefined;
  const canDeleteLadder =
    nodeType === GraphElementType.LADDER &&
    Boolean(currentHorizon) &&
    Boolean(linkedHorizon) &&
    currentHorizon !== linkedHorizon;

  const sourceHorizon = horizons.find((horizon) => horizon.id === ladderSource?.horizonId);
  const targetHorizon = horizons.find((horizon) => horizon.id === ladderTarget?.horizonId);

  const horizonOptions = horizons
    .filter((horizon) => horizon.id !== horizonId)
    .map((horizon) => ({
      value: String(horizon.id),
      label: `${horizon.height} м`,
    }));

  const handleSelectChange = (value: string | null) => {
    if (hasValue(value)) {
      onSelectHorizon(Number(value));
    }
  };

  const handlePointerDown = (event: PointerEvent) => {
    event.stopPropagation();
  };

  const handleConfirmTarget = () => {
    if (!hasValue(horizonId)) return;
    dispatch(graphEditActions.setLadderTarget({ nodeId, horizonId }));
  };

  const handleCancelTarget = () => {
    dispatch(graphEditActions.setLadderTarget(null));
  };

  const ladderLabel =
    sourceHorizon && targetHorizon ? `${sourceHorizon.height} м → ${targetHorizon.height} м` : undefined;

  return (
    <BridgedSceneTooltip position={position}>
      {isSelectingTarget && !isTargetConfirmed && (
        <TooltipButton
          tooltip={ladderLabel ? `Добавить переезд: ${ladderLabel}` : 'Добавить переезд'}
          onClick={handleConfirmTarget}
        >
          <ConfirmIcon />
        </TooltipButton>
      )}

      {isTargetConfirmed && (
        <TooltipButton
          tooltip={ladderLabel ? `Отменить добавление переезда: ${ladderLabel}` : 'Отменить добавление переезда'}
          onClick={handleCancelTarget}
        >
          <TrashIcon />
        </TooltipButton>
      )}

      {canDeleteLadder && (
        <TooltipButton
          tooltip={
            currentHorizon && linkedHorizon
              ? `Удалить переезд: ${currentHorizon.height} м → ${linkedHorizon.height} м`
              : 'Удалить переезд'
          }
          onClick={onDeleteLadder}
        >
          <TrashIcon />
        </TooltipButton>
      )}

      <TooltipButton
        tooltip="Закрыть"
        onClick={onClose}
      >
        <CrossIcon />
      </TooltipButton>

      {!isSelectingTarget && (
        <div
          className={styles.select_wrapper}
          onPointerDown={handlePointerDown}
        >
          <Select
            classNames={{
              input: styles.field,
            }}
            value={null}
            data={horizonOptions}
            onChange={handleSelectChange}
            placeholder="Горизонт"
            allowDeselect={false}
            withCheckIcon={false}
            labelPosition="vertical"
            variant="default"
            inputSize="xs"
            comboboxProps={{ withinPortal: false, offset: 6 }}
          />
        </div>
      )}
    </BridgedSceneTooltip>
  );
}
