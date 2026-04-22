import { useGetAllHorizonsQuery } from '@/shared/api/endpoints/horizons';
import { useConnectLadderNodesMutation } from '@/shared/api/endpoints/ladder-nodes';
import { isHTTPError } from '@/shared/api/types';
import CheckIcon from '@/shared/assets/icons/ic-confirm.svg?react';
import PencilIcon from '@/shared/assets/icons/ic-pencil.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { useConfirm } from '@/shared/lib/confirm';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { AppButton } from '@/shared/ui/AppButton';
import { Collapsible } from '@/shared/ui/Collapsible';
import { toast } from '@/shared/ui/Toast';

import { useExitGraphEdit } from '../../../../lib/hooks/useExitGraphEdit';
import { useTreeNodeExpanded } from '../../../../lib/hooks/useTreeNodeExpanded';
import {
  graphEditActions,
  selectCanSaveLadder,
  selectIsLadderDirty,
  selectIsLadderEditActive,
  selectLadderSource,
  selectLadderTarget,
} from '../../../../model/graph';
import { TreeNode } from '../../../../model/types';

import styles from './LaddersSection.module.css';

/**
 * Секция «Переезды» — сворачиваемый блок с кнопкой редактирования переездов.
 */
export function LaddersSection() {
  const dispatch = useAppDispatch();
  const [isExpanded, toggle] = useTreeNodeExpanded(TreeNode.LADDERS);
  const confirm = useConfirm();

  const isLadderEditActive = useAppSelector(selectIsLadderEditActive);
  const isLadderDirty = useAppSelector(selectIsLadderDirty);
  const ladderSource = useAppSelector(selectLadderSource);
  const ladderTarget = useAppSelector(selectLadderTarget);

  const canSave = useAppSelector(selectCanSaveLadder);

  const { data: horizonsData } = useGetAllHorizonsQuery();
  const horizons = horizonsData?.items ?? EMPTY_ARRAY;

  const exitGraphEdit = useExitGraphEdit();

  const [connectLadderNodes, { isLoading: isSaving }] = useConnectLadderNodesMutation();

  const handleEditToggle = async () => {
    const canProceed = await exitGraphEdit(
      'Для редактирования переездов необходимо выйти из режима редактирования дорог. Несохранённые изменения будут потеряны.',
    );
    if (!canProceed) return;

    if (isLadderDirty) {
      const confirmed = await confirm({
        title: 'Несохранённые изменения',
        message: 'Изменения переездов будут потеряны. Продолжить?',
        confirmText: 'Продолжить',
        cancelText: 'Отмена',
      });
      if (!confirmed) return;
    }

    dispatch(graphEditActions.setLadderEditActive(!isLadderEditActive));
  };

  const handleSave = async () => {
    if (!ladderSource || !ladderTarget) return;

    try {
      await connectLadderNodes({
        from_node_id: ladderSource.nodeId,
        to_node_id: ladderTarget.nodeId,
      }).unwrap();

      const sourceHorizonName = horizons.find((horizon) => horizon.id === ladderSource.horizonId)?.name;
      const targetHorizonName = horizons.find((horizon) => horizon.id === ladderTarget.horizonId)?.name;
      const horizonDetails =
        sourceHorizonName && targetHorizonName ? `c «${sourceHorizonName}» на «${targetHorizonName}»` : '';

      toast.success({ message: `Переезд ${horizonDetails} успешно добавлен.` });

      dispatch(graphEditActions.setLadderEditActive(false));
    } catch (error) {
      const detail = isHTTPError(error) ? error.detail : undefined;
      const errorDetails = typeof detail === 'string' ? `Ошибка: ${detail}` : '';

      toast.error({ message: `Не удалось сохранить, попробуйте еще раз. ${errorDetails}` });
    }
  };

  return (
    <Collapsible
      className={styles.collapsible_road}
      label="Переезды"
      opened={isExpanded}
      onToggle={toggle}
    >
      <div className={styles.road_buttons}>
        <AppButton
          variant={isLadderEditActive ? 'primary' : 'clear'}
          size="xs"
          className={styles.button}
          onClick={handleEditToggle}
        >
          <PencilIcon className={styles.button_icon} />
          Редактировать
        </AppButton>

        {isLadderEditActive && (
          <AppButton
            variant="primary"
            size="xs"
            className={cn(styles.button, styles.button_submit)}
            onClick={handleSave}
            disabled={!canSave || isSaving}
          >
            <CheckIcon className={styles.button_icon} />
            Сохранить
          </AppButton>
        )}
      </div>
    </Collapsible>
  );
}
