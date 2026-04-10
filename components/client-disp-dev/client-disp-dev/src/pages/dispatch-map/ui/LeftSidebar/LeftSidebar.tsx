import { Header } from '@/widgets/page-layout';

import { useConfirm } from '@/shared/lib/confirm';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { AppRoutes } from '@/shared/routes/router';
import { ScrollArea } from '@/shared/ui/ScrollArea';

import { graphEditActions, selectIsGraphDirty } from '../../model/graph';
import { selectHasUnsavedChanges, selectIsGraphEditActive, selectMapMode } from '../../model/selectors';
import { mapActions } from '../../model/slice';
import type { ModeValue } from '../../model/types';
import { Mode } from '../../model/types';

import { EditModeContent } from './EditModeContent';
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

  const isGraphEditActive = useAppSelector(selectIsGraphEditActive);
  const isGraphDirty = useAppSelector(selectIsGraphDirty);

  const changeMode = (mode: ModeValue) => {
    dispatch(mapActions.setMode(mode));
    dispatch(mapActions.setFormTarget(null));
    dispatch(mapActions.setHasUnsavedChanges(false));
    dispatch(graphEditActions.resetDraft());
    if (isGraphEditActive) {
      dispatch(mapActions.toggleGraphEdit());
    }
  };

  const handleModeChange = async (newMode: ModeValue) => {
    if (mode === Mode.EDIT && newMode !== Mode.EDIT && (hasUnsavedChanges || isGraphDirty)) {
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

  return (
    <aside className={styles.sidebar}>
      <Header
        className={styles.page_header}
        routeKey={AppRoutes.DISPATCH_MAP}
        showPinButton={false}
      >
        <HorizonSelect />
      </Header>

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
        {mode === Mode.HISTORY && <p>Режим истории (в разработке)</p>}
      </ScrollArea>
    </aside>
  );
}
