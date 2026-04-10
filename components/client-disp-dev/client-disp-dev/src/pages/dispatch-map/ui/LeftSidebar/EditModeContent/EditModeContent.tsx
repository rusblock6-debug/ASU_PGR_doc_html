import { ObjectsPanel } from '../ObjectsPanel';

import { BackgroundLayerSection } from './BackgroundLayerSection';
import styles from './EditModeContent.module.css';
import { RoadSection } from './RoadSection';

/**
 * Контент режима «Редактирование» — панель объектов, секция дорог и подложка карты.
 */
export function EditModeContent() {
  return (
    <>
      <ObjectsPanel />

      <hr className={styles.line} />

      <RoadSection />

      <hr className={styles.line} />

      <BackgroundLayerSection />
    </>
  );
}
