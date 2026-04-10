import { Page } from '@/widgets/page-layout';

import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { useDataLossBlocker } from '@/shared/lib/hooks/useDataLossBlocker';
import { ResizablePanel, ResizablePanelGroup } from '@/shared/ui/Resizable';

import { useMapVehicles } from '../../lib/hooks/useMapVehicles';
import { useWebSocket } from '../../lib/hooks/useWebSocket';
import { graphEditActions, selectIsGraphDirty } from '../../model/graph';
import { selectHasUnsavedChanges, selectIsGraphEditActive } from '../../model/selectors';
import { mapActions } from '../../model/slice';
import { Compass } from '../Compass';
import { GroundPointerProvider } from '../GroundPointerProvider';
import { LeftSidebar } from '../LeftSidebar';
import { MapCameraProvider } from '../MapCameraProvider';
import { MapScene } from '../MapScene';
import { MapTooltipOverlay } from '../MapScene/MapTooltip';
import { ObjectEditor } from '../ObjectEditor';
import { StatusBar } from '../StatusBar';
import { Toolbar } from '../Toolbar';

import styles from './MapPage.module.css';

/**
 * Представляет компонент страницы «Карта».
 */
export function MapPage() {
  const dispatch = useAppDispatch();
  const hasUnsavedChanges = useAppSelector(selectHasUnsavedChanges);
  const isGraphDirty = useAppSelector(selectIsGraphDirty);
  const isGraphEditActive = useAppSelector(selectIsGraphEditActive);

  const { all: vehiclesList } = useMapVehicles();

  const { vehicles } = useWebSocket({
    vehiclesList,
  });

  const onReset = () => {
    dispatch(mapActions.setFormTarget(null));
    dispatch(mapActions.setHasUnsavedChanges(false));
    dispatch(mapActions.setPlacementPlaceToAdd(null));
    dispatch(graphEditActions.resetDraft());
    if (isGraphEditActive) {
      dispatch(mapActions.toggleGraphEdit());
    }
  };

  useDataLossBlocker({
    hasUnsavedChanges: hasUnsavedChanges || isGraphDirty,
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
                <MapScene vehicles={vehicles} />

                <MapTooltipOverlay />

                <Toolbar />

                <StatusBar>
                  <Compass />
                </StatusBar>
              </ResizablePanel>

              <ObjectEditor />
            </ResizablePanelGroup>
          </div>
        </GroundPointerProvider>
      </MapCameraProvider>
    </Page>
  );
}
