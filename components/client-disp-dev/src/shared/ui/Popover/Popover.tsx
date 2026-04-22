import {
  type PopoverProps,
  type PopoverTargetProps,
  type PopoverDropdownProps,
  Popover as MantinePopover,
} from '@mantine/core';

import styles from './Popover.module.css';

/**
 * Представляет компонент выпадающего окна.
 */
function Popover(props: Readonly<PopoverProps>) {
  return (
    <MantinePopover
      {...props}
      classNames={{
        dropdown: styles.dropdown,
      }}
    />
  );
}

/**
 * PopoverTarget - обертка для целевого элемента всплывающего окна.
 */
function PopoverTarget({ children, ...props }: Readonly<PopoverTargetProps>) {
  return <MantinePopover.Target {...props}>{children}</MantinePopover.Target>;
}

/**
 * PopoverDropdown - обертка для всплывающего окна.
 */
function PopoverDropdown({ children, ...props }: Readonly<PopoverDropdownProps>) {
  return <MantinePopover.Dropdown {...props}>{children}</MantinePopover.Dropdown>;
}

// Присваиваем вложенные компоненты как свойства основного компонента для совместимости с API Mantine
const PopoverWithComponents = Object.assign(Popover, {
  Target: PopoverTarget,
  Dropdown: PopoverDropdown,
});

export { PopoverWithComponents as Popover, PopoverTarget, PopoverDropdown };
