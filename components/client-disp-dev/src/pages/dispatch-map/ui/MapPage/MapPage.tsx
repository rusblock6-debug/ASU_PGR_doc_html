import { Page } from '@/widgets/page-layout';

import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { useDataLossBlocker } from '@/shared/lib/hooks/useDataLossBlocker';
import { ResizablePanel, ResizablePanelGroup } from '@/shared/ui/Resizable';

import { useMapDataLoading } from '../../lib/hooks/useMapDataLoading';
import { graphEditActions, selectIsColorDirty, selectIsGraphDirty, selectIsLadderDirty } from '../../model/graph';
import { selectHasUnsavedChanges, selectIsGraphEditActive } from '../../model/selectors';
import { mapActions } from '../../model/slice';
import { Compass } from '../Compass';
import { GroundPointerProvider } from '../GroundPointerProvider';
import { HistoryPlayer } from '../HistoryPlayer';
import { LeftSidebar } from '../LeftSidebar';
import { MapCameraProvider } from '../MapCameraProvider';
import { MapScene } from '../MapScene';
import { MapLoader } from '../MapScene/MapLoader';
import { MapTooltipOverlay } from '../MapScene/MapTooltip';
import { ObjectEditor } from '../ObjectEditor';
import { StatusBar } from '../StatusBar';
import { Toolbar } from '../Toolbar';
import { VehicleContextMenu } from '../VehicleContextMenu';

import styles from './MapPage.module.css';

/**
 * Представляет компонент страницы «Карта».
 */
export function MapPage() {
  const dispatch = useAppDispatch();
  const hasUnsavedChanges = useAppSelector(selectHasUnsavedChanges);
  const isGraphDirty = useAppSelector(selectIsGraphDirty);
  const isColorDirty = useAppSelector(selectIsColorDirty);
  const isGraphEditActive = useAppSelector(selectIsGraphEditActive);
  const isLadderDirty = useAppSelector(selectIsLadderDirty);

  const isLoading = useMapDataLoading();

  const onReset = () => {
    dispatch(mapActions.setFormTarget(null));
    dispatch(mapActions.setHasUnsavedChanges(false));
    dispatch(mapActions.setPlacementPlaceToAdd(null));
    dispatch(graphEditActions.resetDraft());
    dispatch(graphEditActions.setLadderEditActive(false));
    if (isGraphEditActive) {
      dispatch(mapActions.toggleGraphEdit());
    }
  };

  useDataLossBlocker({
    hasUnsavedChanges: hasUnsavedChanges || isGraphDirty || isColorDirty || isLadderDirty,
    onReset,
  });

  return (
    <Page variant="table">
      <MapCameraProvider>
        <GroundPointerProvider>
          <div className={styles.body}>
            <LeftSidebar />

            <ResizablePanelGroup>
              <ResizablePanel
                id="map"
                notifyOnResize
                className={styles.map_panel}
              >
                <MapLoader showLoader={isLoading} />

                <MapScene />

                <MapTooltipOverlay />

                <VehicleContextMenu />

                <Toolbar />

                <StatusBar>
                  <Compass />
                </StatusBar>

                <HistoryPlayer />
              </ResizablePanel>

              <ObjectEditor />
            </ResizablePanelGroup>
          </div>
        </GroundPointerProvider>
      </MapCameraProvider>
    </Page>
  );
}
