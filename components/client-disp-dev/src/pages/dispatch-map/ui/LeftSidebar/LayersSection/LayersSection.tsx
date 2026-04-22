import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { Collapsible } from '@/shared/ui/Collapsible';

import { useTreeNodeExpanded } from '../../../lib/hooks/useTreeNodeExpanded';
import { selectMapLayers } from '../../../model/selectors';
import { mapActions } from '../../../model/slice';
import { MapLayer, TreeNode } from '../../../model/types';
import type { MapLayerValue } from '../../../model/types';

import styles from './LayersSection.module.css';
import { LayerToggle } from './LayerToggle';

const LAYER_CONFIG: { key: MapLayerValue; label: string }[] = [
  { key: MapLayer.ROADS, label: 'Дороги' },
  { key: MapLayer.BACKGROUND, label: 'Подложка карты' },
] satisfies readonly { key: MapLayerValue; label: string }[];

/**
 * Секция переключения видимости слоёв карты.
 */
export function LayersSection() {
  const dispatch = useAppDispatch();
  const layers = useAppSelector(selectMapLayers);
  const [isLayersExpanded, toggleLayers] = useTreeNodeExpanded(TreeNode.LAYERS);

  const toggleLayer = (layerKey: MapLayerValue) => {
    dispatch(mapActions.toggleLayerVisibility(layerKey));
  };

  return (
    <Collapsible
      className={styles.collapsible_layers}
      label="Слои карты"
      opened={isLayersExpanded}
      onToggle={toggleLayers}
    >
      <div className={styles.layers}>
        {LAYER_CONFIG.map(({ key, label }) => (
          <LayerToggle
            key={key}
            label={label}
            visible={layers[key]}
            onToggle={() => toggleLayer(key)}
          />
        ))}
      </div>
    </Collapsible>
  );
}
