import { Checkbox as MantineCheckbox, type CheckboxProps as MantineCheckboxProps } from '@mantine/core';

import styles from './Checkbox.module.css';

/**
 * Представляет компонент-обертку для компонента Checkbox.
 */
export function Checkbox(props: Readonly<MantineCheckboxProps>) {
  return (
    <MantineCheckbox
      classNames={{
        root: styles.root,
      }}
      {...props}
    />
  );
}
