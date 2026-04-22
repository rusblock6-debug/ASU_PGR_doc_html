import { Header } from '@/widgets/page-layout';

import ArrowIcon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { useConfirm } from '@/shared/lib/confirm';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { useUserLocalStorage } from '@/shared/lib/hooks/useUserLocalStorage';
import { AppRoutes } from '@/shared/routes/router';
import { AppButton } from '@/shared/ui/AppButton';
import { ScrollArea } from '@/shared/ui/ScrollArea';

import { SIDEBAR_COLLAPSED_KEY } from '../../config/sidebar';
import { graphEditActions, selectIsColorDirty, selectIsGraphDirty, selectIsLadderDirty } from '../../model/graph';
import {
  selectHasUnsavedChanges,
  selectIsGraphEditActive,
  selectIsPlayHistoryPlayer,
  selectMapMode,
} from '../../model/selectors';
import { mapActions } from '../../model/slice';
import type { ModeValue } from '../../model/types';
import { Mode } from '../../model/types';

import { EditModeContent } from './EditModeContent';
import { HistoryModeContent } from './HistoryModeContent';
import { HorizonSelect } from './HorizonSelect';
import styles from './LeftSidebar.module.css';
import { ModeSwitcher } from './ModeSwitcher';
import { ViewModeContent } from './ViewModeContent';

/**
 * Левый сайдбар страницы карты.
 *
 * Содержит переключатель режимов (просмотр / редактирование / история)
 * и контент текущего режима.
 */
export function LeftSidebar() {
  const confirm = useConfirm();
  const dispatch = useAppDispatch();
  const mode = useAppSelector(selectMapMode);
  const hasUnsavedChanges = useAppSelector(selectHasUnsavedChanges);
  const isPlayHistoryPlayer = useAppSelector(selectIsPlayHistoryPlayer);

  const isGraphEditActive = useAppSelector(selectIsGraphEditActive);
  const isGraphDirty = useAppSelector(selectIsGraphDirty);
  const isColorDirty = useAppSelector(selectIsColorDirty);
  const isLadderDirty = useAppSelector(selectIsLadderDirty);

  const [isCollapsed, setIsCollapsed] = useUserLocalStorage(SIDEBAR_COLLAPSED_KEY, false);

  const changeMode = (mode: ModeValue) => {
    dispatch(mapActions.setMode(mode));
    dispatch(mapActions.setFormTarget(null));
    dispatch(mapActions.setHasUnsavedChanges(false));
    dispatch(graphEditActions.resetDraft());
    dispatch(graphEditActions.setLadderEditActive(false));
    if (isGraphEditActive) {
      dispatch(mapActions.toggleGraphEdit());
    }
    if (isPlayHistoryPlayer) {
      dispatch(mapActions.togglePlayHistoryPlayer(false));
    }
  };

  const handleModeChange = async (newMode: ModeValue) => {
    if (
      mode === Mode.EDIT &&
      newMode !== Mode.EDIT &&
      (hasUnsavedChanges || isGraphDirty || isColorDirty || isLadderDirty)
    ) {
      const isConfirmed = await confirm({
        title: 'Вы действительно хотите выйти из режима редактирования?',
        message: `Текущие изменения будут утеряны.`,
        confirmText: 'Продолжить',
        cancelText: 'Отмена',
        size: 'md',
      });

      if (isConfirmed) {
        changeMode(newMode);
      }

      return;
    }

    changeMode(newMode);
  };

  const handleCollapseSidebar = () => {
    setIsCollapsed((prev) => !prev);
  };

  return (
    <aside className={cn(styles.sidebar, { [styles.sidebar_collapsed]: isCollapsed })}>
      <Header
        className={styles.page_header}
        routeKey={AppRoutes.DISPATCH_MAP}
        showPinButton={false}
      >
        <HorizonSelect />

        <AppButton
          title={isCollapsed ? 'Развернуть панель' : 'Свернуть панель'}
          size="xs"
          variant="primary"
          onlyIcon
          className={cn(styles.collapse_button, { [styles.active]: isCollapsed })}
          onClick={handleCollapseSidebar}
        >
          <ArrowIcon />
        </AppButton>
      </Header>

      {!isCollapsed && (
        <>
          <ModeSwitcher
            className={styles.mode_switcher}
            activeMode={mode}
            onModeChange={handleModeChange}
          />

          <ScrollArea
            className={styles.body}
            scrollbars="y"
            scrollbarSize={4}
          >
            {mode === Mode.VIEW && <ViewModeContent />}
            {mode === Mode.EDIT && <EditModeContent />}
            {mode === Mode.HISTORY && <HistoryModeContent />}
          </ScrollArea>
        </>
      )}
    </aside>
  );
}
