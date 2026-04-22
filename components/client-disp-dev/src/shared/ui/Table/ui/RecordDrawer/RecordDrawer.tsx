import { useState } from 'react';

import { useDataLossBlocker } from '@/shared/lib/hooks/useDataLossBlocker';
import { Drawer } from '@/shared/ui/Drawer';

import { useTableContext } from '../../model/TableContext';
import { RecordForm } from '../RecordForm';

export function RecordDrawer<TData>() {
  const { columns, drawerMode, editingRow, formAddTitle, formEditTitle, closeDrawer, onAdd, onEdit, getRowId } =
    useTableContext<TData>();

  const [isDirty, setIsDirty] = useState(false);

  const { forceBlocker } = useDataLossBlocker({ hasUnsavedChanges: isDirty });

  const handleClose = async () => {
    const canClose = await forceBlocker();
    if (canClose) {
      setIsDirty(false);
      closeDrawer();
    }
  };

  const handleSubmit = async (data: Partial<TData>) => {
    if (drawerMode === 'add') {
      await onAdd?.(data);
    } else if (drawerMode === 'edit' && editingRow) {
      const id = getRowId(editingRow);
      await onEdit?.(id, data);
    }
    setIsDirty(false);
    closeDrawer();
  };

  const isOpen = drawerMode !== 'closed';
  const title = drawerMode === 'add' ? formAddTitle : formEditTitle;

  return (
    <Drawer.Root
      size={620}
      opened={isOpen}
      onClose={handleClose}
      position="right"
    >
      <Drawer.Overlay />
      <Drawer.Content>
        <Drawer.Header>
          <Drawer.Title>{title}</Drawer.Title>
          <Drawer.CloseButton />
        </Drawer.Header>
        <Drawer.Body>
          {isOpen && (
            <RecordForm
              columns={columns}
              initialData={drawerMode === 'edit' && editingRow ? editingRow : undefined}
              onSubmit={handleSubmit}
              onDirtyChange={setIsDirty}
              mode={drawerMode}
            />
          )}
        </Drawer.Body>
      </Drawer.Content>
    </Drawer.Root>
  );
}
