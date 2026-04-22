import { LayersSection } from '../LayersSection';
import { ObjectsPanel } from '../ObjectsPanel';

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
