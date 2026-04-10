import { ObjectsPanel } from '../ObjectsPanel';

import { LayersSection } from './LayersSection';

/**
 * Контент режима «Просмотр» — дерево объектов карты и панель слоёв.
 */
export function ViewModeContent() {
  return (
    <>
      <ObjectsPanel />
      <LayersSection />
    </>
  );
}
