import type {
  MenuDividerProps,
  MenuDropdownProps,
  MenuItemProps,
  MenuLabelProps,
  MenuProps,
  MenuTargetProps,
  MenuSubProps,
  MenuSubTargetProps,
  MenuSubItemProps,
  MenuSubDropdownProps,
} from '@mantine/core';
import { Menu as MantineMenu } from '@mantine/core';

import { Z_INDEX } from '@/shared/lib/constants';

import styles from './Menu.module.css';

/**
 * Представляет компонент-обертку для меню.
 */
function Menu({
  className,
  children,
  shadow = 'none',
  zIndex = Z_INDEX.STICKY,
  offset = 2,
  ...props
}: MenuProps & {
  readonly className?: string;
}) {
  return (
    <MantineMenu
      shadow={shadow}
      zIndex={zIndex}
      offset={offset}
      classNames={{
        dropdown: styles.dropdown,
        item: styles.item,
      }}
      {...props}
    >
      {children}
    </MantineMenu>
  );
}

/**
 * MenuTarget - обертка для целевого элемента меню
 */
function MenuTarget({ children, ...props }: Readonly<MenuTargetProps>) {
  return <MantineMenu.Target {...props}>{children}</MantineMenu.Target>;
}

/**
 * MenuDropdown - обертка для выпадающего списка меню
 */
function MenuDropdown({ className, children, ...props }: Readonly<MenuDropdownProps>) {
  return (
    <MantineMenu.Dropdown
      className={className}
      {...props}
    >
      {children}
    </MantineMenu.Dropdown>
  );
}

/**
 * MenuItem - обертка для элемента меню
 */
function MenuItem({ className, children, ...props }: Readonly<MenuItemProps>) {
  return (
    <MantineMenu.Item
      className={className}
      {...props}
    >
      {children}
    </MantineMenu.Item>
  );
}

/**
 * MenuLabel - обертка для метки (заголовка) группы элементов меню
 */
function MenuLabel({ className, children, ...props }: Readonly<MenuLabelProps>) {
  return (
    <MantineMenu.Label
      className={className}
      {...props}
    >
      {children}
    </MantineMenu.Label>
  );
}

/**
 * MenuDivider - обертка для разделителя элементов меню
 */
function MenuDivider({ className, ...props }: Readonly<MenuDividerProps>) {
  return (
    <MantineMenu.Divider
      className={className}
      {...props}
    />
  );
}

/**
 * MenuSub - обертка для подменю.
 */
function MenuSub({ children, ...props }: Readonly<MenuSubProps>) {
  return <MantineMenu.Sub {...props}>{children}</MantineMenu.Sub>;
}

/**
 * MenuSubTarget - обертка для целевого элемента подменю.
 */
function MenuSubTarget({ children, ...props }: Readonly<MenuSubTargetProps>) {
  return <MantineMenu.Sub.Target {...props}>{children}</MantineMenu.Sub.Target>;
}

/**
 * MenuSubItem - обертка для элемента подменю.
 */
function MenuSubItem({ children, ...props }: Readonly<MenuSubItemProps>) {
  return <MantineMenu.Sub.Item {...props}>{children}</MantineMenu.Sub.Item>;
}

/**
 * MenuSubDropdown - обертка для выпадающего списка подменю.
 */
function MenuSubDropdown({ children, ...props }: Readonly<MenuSubDropdownProps>) {
  return <MantineMenu.Sub.Dropdown {...props}>{children}</MantineMenu.Sub.Dropdown>;
}

const SubMenuWithComponents = Object.assign(MenuSub, {
  Target: MenuSubTarget,
  Dropdown: MenuSubDropdown,
  Item: MenuSubItem,
});

// Присваиваем вложенные компоненты как свойства основного компонента для совместимости с API Mantine
const MenuWithComponents = Object.assign(Menu, {
  Target: MenuTarget,
  Dropdown: MenuDropdown,
  Item: MenuItem,
  Label: MenuLabel,
  Divider: MenuDivider,
  Sub: SubMenuWithComponents,
});

export { MenuWithComponents as Menu };
