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
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { AppButton } from '@/shared/ui/AppButton';
import { Collapsible } from '@/shared/ui/Collapsible';
import { ColorPicker } from '@/shared/ui/ColorPicker';
import { Popover } from '@/shared/ui/Popover';
import { toast } from '@/shared/ui/Toast';

import { useTreeNodeExpanded } from '../../../../lib/hooks/useTreeNodeExpanded';
import { editorToServer, graphEditActions, selectDraft, selectIsGraphDirty } from '../../../../model/graph';
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
  const isGraphEditActive = useAppSelector(selectIsGraphEditActive);
  const isRulerActive = useAppSelector(selectIsRulerActive);
  const isDirty = useAppSelector(selectIsGraphDirty);
  const draft = useAppSelector(selectDraft);

  const horizonId = useAppSelector(selectSelectedHorizonId);
  const {
    data: graphData,
    isLoading: isGraphLoading,
    isError: isGraphError,
  } = useGetHorizonGraphQuery(horizonId ?? skipToken);

  const [updateHorizonGraph, { isLoading: isGraphSaving }] = useUpdateHorizonGraphMutation();
  const [updateHorizon, { isLoading: isColorSaving }] = useUpdateHorizonMutation();

  const [colorPopoverOpened, setColorPopoverOpened] = useState(false);
  const [draftColor, setDraftColor] = useState('');

  const originalColor = graphData?.horizon.color ?? '';
  const isColorDirty = draftColor !== '' && draftColor !== originalColor;
  const isSaving = isGraphSaving || isColorSaving;

  const isEditDisabled = isGraphLoading || isGraphError || !graphData;

  const handleEditToggle = async () => {
    if (isGraphEditActive && isDirty) {
      const confirmed = await confirm({
        title: 'Несохранённые изменения',
        message: 'Изменения дорог будут потеряны. Продолжить?',
        confirmText: 'Продолжить',
        cancelText: 'Отмена',
      });

      if (!confirmed) return;
    }

    if (isRulerActive && !isGraphEditActive) {
      const confirmed = await confirm({
        title: 'Линейка активна',
        message: 'Для редактирования дорог необходимо закрыть линейку. Данные измерений линейки будут потеряны.',
        confirmText: 'Продолжить',
        cancelText: 'Отмена',
        size: 'md',
      });

      if (!confirmed) return;

      dispatch(mapActions.toggleRuler());
    }

    if (!isGraphEditActive && graphData) {
      dispatch(graphEditActions.initDraft(graphData));
    } else {
      dispatch(graphEditActions.resetDraft());
    }

    dispatch(mapActions.toggleGraphEdit());
  };

  const handleSave = async () => {
    if (!horizonId) return;

    const colorChanged = draftColor !== '' && draftColor !== originalColor;

    if (isDirty && draft) {
      try {
        await updateHorizonGraph({ horizonId, body: editorToServer(draft) }).unwrap();
        toast.success({ message: 'Изменения дорог сохранены' });
        dispatch(graphEditActions.resetDraft());
        dispatch(mapActions.toggleGraphEdit());
      } catch {
        toast.error({ message: 'Не удалось сохранить, попробуйте еще раз' });
      }
    }

    if (colorChanged) {
      try {
        await updateHorizon({ horizonId, body: { color: draftColor } }).unwrap();
        toast.success({ message: 'Цвет дороги обновлён' });
        setColorPopoverOpened(false);
        setDraftColor('');
        dispatch(mapActions.setHasUnsavedChanges(false));
      } catch {
        toast.error({ message: 'Не удалось обновить цвет, попробуйте еще раз' });
      }
    }
  };

  const handleColorChange = (value: string) => {
    setDraftColor(value);
  };

  const handleColorChangeEnd = (value: string) => {
    dispatch(graphEditActions.setPreviewColor(value));
    dispatch(mapActions.setHasUnsavedChanges(true));
  };

  const handleColorPopoverOpen = () => {
    setDraftColor(originalColor);
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
              value={draftColor}
              onChange={handleColorChange}
              onChangeEnd={handleColorChangeEnd}
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
