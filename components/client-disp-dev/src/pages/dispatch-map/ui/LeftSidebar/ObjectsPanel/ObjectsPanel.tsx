import { type ChangeEvent, useState } from 'react';

import LoupeIcon from '@/shared/assets/icons/ic-loupe.svg?react';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { Collapsible } from '@/shared/ui/Collapsible';
import { TextInput } from '@/shared/ui/TextInput';

import { useTreeNodeExpanded } from '../../../lib/hooks/useTreeNodeExpanded';
import { selectMapMode } from '../../../model/selectors';
import { Mode, TreeNode } from '../../../model/types';

import { EquipmentSection } from './EquipmentSection';
import { HorizonSwitcher } from './HorizonSwitcher';
import styles from './ObjectsPanel.module.css';
import { PlacesSection } from './PlacesSection';

/**
 * Панель объектов карты — сворачиваемый блок с поиском, переключателем горизонта,
 * секциями «Оборудование предприятия» и «Места».
 */
export function ObjectsPanel() {
  const mode = useAppSelector(selectMapMode);

  const [isObjectsExpanded, toggleObjects] = useTreeNodeExpanded(TreeNode.OBJECTS);
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearchChange = (e: ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.currentTarget.value);
  };

  const handleSearchClear = () => {
    setSearchQuery('');
  };

  return (
    <Collapsible
      label="Объекты"
      opened={isObjectsExpanded}
      onToggle={toggleObjects}
      rightSection={<HorizonSwitcher />}
    >
      <TextInput
        className={styles.search}
        styles={{ input: { ['--input-padding']: '30px', ['--input-height']: '26px' } }}
        leftSection={<LoupeIcon className={styles.search_icon} />}
        placeholder="Поиск объектов"
        variant="outline"
        size="xs"
        labelPosition="vertical"
        value={searchQuery}
        onChange={handleSearchChange}
        clearable={searchQuery.length > 0}
        onClear={handleSearchClear}
      />

      <EquipmentSection
        classNames={{
          root: styles.section,
          children: styles.children,
        }}
        searchQuery={searchQuery}
      />

      {mode !== Mode.HISTORY && (
        <PlacesSection
          classNames={{
            root: styles.section,
            children: styles.children,
          }}
          searchQuery={searchQuery}
        />
      )}
    </Collapsible>
  );
}
