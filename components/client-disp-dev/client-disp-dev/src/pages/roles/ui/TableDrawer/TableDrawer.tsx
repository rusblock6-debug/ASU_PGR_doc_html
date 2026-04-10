import { type Role } from '@/shared/api/endpoints/roles';
import { Drawer } from '@/shared/ui/Drawer';

import { CreateEditForm } from '../CreateEditForm';

/** Режимы отображения компонента. */
export type DrawerMode = 'closed' | 'add' | 'edit';

/**
 * Представляет свойства компонента для отображения формы создания/редактирования роли.
 */
interface TableDrawerProps {
  /** Возвращает режим. */
  readonly drawerMode: DrawerMode;
  /** Возвращает делегат вызываемый при закрытии. */
  readonly onClose: () => void;
  /** Возвращает роль. */
  readonly role: Role | null;
}

/**
 * Представляет компонент для отображения формы создания/редактирования роли.
 */
export function TableDrawer(props: TableDrawerProps) {
  const { drawerMode, onClose, role } = props;

  const isOpen = drawerMode !== 'closed';
  const isAddMode = drawerMode === 'add';

  return (
    <Drawer.Root
      size={620}
      opened={isOpen}
      onClose={onClose}
      position="right"
    >
      <Drawer.Overlay />
      <Drawer.Content>
        <Drawer.Header>
          <Drawer.Title>{isAddMode ? 'Новая роль' : role?.name}</Drawer.Title>
          <Drawer.CloseButton />
        </Drawer.Header>
        <Drawer.Body>
          {isOpen && (
            <CreateEditForm
              role={role}
              onClose={onClose}
              addMode={drawerMode === 'add'}
            />
          )}
        </Drawer.Body>
      </Drawer.Content>
    </Drawer.Root>
  );
}
