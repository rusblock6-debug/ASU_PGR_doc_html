import { skipToken } from '@reduxjs/toolkit/query';
import { useState } from 'react';

import {
  useGetHorizonGraphQuery,
  useUpdateHorizonGraphMutation,
  useUpdateHorizonMutation,
} from '@/shared/api/endpoints/horizons';
import CheckIcon from '@/shared/assets/icons/ic-confirm.svg?react';
import PaletteIcon from '@/shared/assets/icons/ic-palette.svg?react';
import PencilIcon from '@/shared/assets/icons/ic-pencil.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { useConfirm } from '@/shared/lib/confirm';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { AppButton } from '@/shared/ui/AppButton';
import { Collapsible } from '@/shared/ui/Collapsible';
import { ColorPicker } from '@/shared/ui/ColorPicker';
import { Popover } from '@/shared/ui/Popover';
import { toast } from '@/shared/ui/Toast';

import { useExitFormEdit } from '../../../../lib/hooks/useExitFormEdit';
import { useTreeNodeExpanded } from '../../../../lib/hooks/useTreeNodeExpanded';
import {
  editorToServer,
  graphEditActions,
  selectDraft,
  selectIsGraphDirty,
  selectIsLadderEditActive,
  selectIsLadderDirty,
  selectPreviewColor,
} from '../../../../model/graph';
import { selectIsGraphEditActive, selectIsRulerActive, selectSelectedHorizonId } from '../../../../model/selectors';
import { mapActions } from '../../../../model/slice';
import { TreeNode } from '../../../../model/types';

import styles from './RoadSection.module.css';

/**
 * Секция «Дороги» — сворачиваемый блок с кнопками редактирования и смены цвета дорог.
 */
export function RoadSection() {
  const [isExpanded, toggle] = useTreeNodeExpanded(TreeNode.ROADS);
  const dispatch = useAppDispatch();
  const confirm = useConfirm();
  const exitFormEdit = useExitFormEdit();
  const isGraphEditActive = useAppSelector(selectIsGraphEditActive);
  const isRulerActive = useAppSelector(selectIsRulerActive);
  const isDirty = useAppSelector(selectIsGraphDirty);
  const draft = useAppSelector(selectDraft);

  const isLadderEditActive = useAppSelector(selectIsLadderEditActive);
  const isLadderDirty = useAppSelector(selectIsLadderDirty);

  const horizonId = useAppSelector(selectSelectedHorizonId);
  const {
    data: graphData,
    isLoading: isGraphLoading,
    isError: isGraphError,
    refetch: refetchGraph,
  } = useGetHorizonGraphQuery(horizonId ?? skipToken);

  const [updateHorizonGraph, { isLoading: isGraphSaving }] = useUpdateHorizonGraphMutation();
  const [updateHorizon, { isLoading: isColorSaving }] = useUpdateHorizonMutation();

  const previewColor = useAppSelector(selectPreviewColor);
  const [colorPopoverOpened, setColorPopoverOpened] = useState(false);

  const [isSaveInProgress, setIsSaveInProgress] = useState(false);

  const originalColor = graphData?.horizon.color ?? '';
  const isColorDirty = hasValue(previewColor) && previewColor !== originalColor;
  const isSaving = isGraphSaving || isColorSaving || isSaveInProgress;

  const isEditDisabled = isGraphLoading || isGraphError || !graphData;

  const confirmDiscardLadderEdits = async () => {
    if (!isLadderEditActive) return true;

    if (isLadderDirty) {
      const confirmed = await confirm({
        title: 'Несохранённые изменения',
        message: 'Изменения переездов будут потеряны. Продолжить?',
        confirmText: 'Продолжить',
        cancelText: 'Отмена',
      });

      if (!confirmed) return false;
    }

    dispatch(graphEditActions.setLadderEditActive(false));
    return true;
  };

  const confirmExitForm = async () => {
    if (isGraphEditActive) return true;

    const canProceed = await exitFormEdit('Редактирование объекта будет завершено');
    if (!canProceed) return false;

    dispatch(mapActions.setFormTarget(null));
    dispatch(mapActions.setHasUnsavedChanges(false));
    return true;
  };

  const confirmDiscardGraphEdits = async () => {
    if (!isGraphEditActive || !isDirty) return true;

    return await confirm({
      title: 'Несохранённые изменения',
      message: 'Изменения дорог будут потеряны. Продолжить?',
      confirmText: 'Продолжить',
      cancelText: 'Отмена',
    });
  };

  const confirmCloseRuler = async () => {
    if (isGraphEditActive || !isRulerActive) return true;

    const confirmed = await confirm({
      title: 'Линейка активна',
      message: 'Для редактирования дорог необходимо закрыть линейку. Данные измерений линейки будут потеряны.',
      confirmText: 'Продолжить',
      cancelText: 'Отмена',
      size: 'md',
    });

    if (!confirmed) return false;

    dispatch(mapActions.toggleRuler());
    return true;
  };

  const handleEditToggle = async () => {
    if (!(await confirmDiscardLadderEdits())) return;
    if (!(await confirmExitForm())) return;
    if (!(await confirmDiscardGraphEdits())) return;
    if (!(await confirmCloseRuler())) return;

    if (!isGraphEditActive && graphData) {
      dispatch(graphEditActions.initDraft(graphData));
    } else {
      dispatch(graphEditActions.resetDraft());
    }

    dispatch(mapActions.toggleGraphEdit());
  };

  const handleSave = async () => {
    if (!horizonId) return;

    setIsSaveInProgress(true);

    try {
      if (isDirty && draft) {
        try {
          await updateHorizonGraph({ horizonId, body: editorToServer(draft) }).unwrap();
          await refetchGraph();
          toast.success({ message: 'Изменения дорог сохранены' });
          dispatch(graphEditActions.resetDraft());
          dispatch(mapActions.toggleGraphEdit());
        } catch {
          toast.error({ message: 'Не удалось сохранить, попробуйте еще раз' });
        }
      }

      if (isColorDirty) {
        try {
          await updateHorizon({ horizonId, body: { color: previewColor } }).unwrap();
          await refetchGraph();
          toast.success({ message: 'Цвет дороги обновлён' });
          setColorPopoverOpened(false);
        } catch {
          toast.error({ message: 'Не удалось обновить цвет, попробуйте еще раз' });
        }
      }
    } finally {
      setIsSaveInProgress(false);
    }
  };

  const handleColorChange = (value: string) => {
    dispatch(graphEditActions.setPreviewColor(value));
  };

  const handleColorPopoverOpen = () => {
    setColorPopoverOpened(true);
  };

  const handleColorPopoverClose = () => {
    setColorPopoverOpened(false);
  };

  return (
    <Collapsible
      className={styles.collapsible_road}
      label="Дороги"
      opened={isExpanded}
      onToggle={toggle}
    >
      <div className={styles.road_buttons}>
        <AppButton
          variant={isGraphEditActive ? 'primary' : 'clear'}
          size="xs"
          className={styles.button}
          disabled={isEditDisabled || isSaving}
          onClick={handleEditToggle}
        >
          <PencilIcon className={styles.button_icon} />
          Редактировать
        </AppButton>

        <Popover
          opened={colorPopoverOpened}
          onChange={(next) => {
            if (!next) handleColorPopoverClose();
          }}
          position="bottom-start"
          offset={4}
          withinPortal
        >
          <Popover.Target>
            <AppButton
              variant={colorPopoverOpened ? 'primary' : 'clear'}
              size="xs"
              className={styles.button}
              disabled={isEditDisabled || isSaving}
              onClick={handleColorPopoverOpen}
            >
              <PaletteIcon className={styles.button_icon} />
              Изменить цвет
            </AppButton>
          </Popover.Target>

          <Popover.Dropdown className={styles.color_dropdown}>
            <ColorPicker
              value={previewColor ?? originalColor}
              onChange={handleColorChange}
            />
          </Popover.Dropdown>
        </Popover>

        {(isGraphEditActive || isColorDirty) && (
          <AppButton
            variant="primary"
            size="xs"
            className={cn(styles.button, styles.button_submit)}
            disabled={(!isDirty && !isColorDirty) || isSaving}
            loading={isSaving}
            onClick={handleSave}
          >
            <CheckIcon className={styles.button_icon} />
            Сохранить
          </AppButton>
        )}
      </div>
    </Collapsible>
  );
}
