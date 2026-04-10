import { Collapsible } from '@/shared/ui/Collapsible';
import { TextInput } from '@/shared/ui/TextInput';

import { useTreeNodeExpanded } from '../../../lib/hooks/useTreeNodeExpanded';
import { TreeNode } from '../../../model/types';
import type { HorizonFilterValue } from '../../../model/types';

import { EquipmentSection } from './EquipmentSection';
import { HorizonSwitcher } from './HorizonSwitcher';
import styles from './ObjectsPanel.module.css';
import { PlacesSection } from './PlacesSection';

/**
 * Панель объектов карты — сворачиваемый блок с поиском, переключателем горизонта,
 * секциями «Оборудование предприятия» и «Места».
 */
export function ObjectsPanel() {
  const [isObjectsExpanded, toggleObjects] = useTreeNodeExpanded(TreeNode.OBJECTS);

  return (
    <Collapsible
      label="Объекты"
      opened={isObjectsExpanded}
      onToggle={toggleObjects}
      rightSection={
        <HorizonSwitcher
          activeHorizon="all"
          onHorizonChange={(_horizon: HorizonFilterValue) => {
            throw new Error('Function not implemented.');
          }}
        />
      }
    >
      <TextInput
        className={styles.search}
        placeholder="Поиск объектов"
        variant="outline"
        size="xs"
        disabled
        labelPosition="vertical"
      />

      <EquipmentSection
        classNames={{
          root: styles.section,
          children: styles.children,
        }}
      />

      <PlacesSection
        classNames={{
          root: styles.section,
          children: styles.children,
        }}
      />
    </Collapsible>
  );
}
