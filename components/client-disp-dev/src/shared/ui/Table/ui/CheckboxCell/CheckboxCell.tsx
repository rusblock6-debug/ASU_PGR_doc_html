import { Checkbox } from '@mantine/core';
import { type ChangeEvent } from 'react';

import styles from './CheckboxCell.module.css';

export interface CheckboxCellProps {
  readonly checked: boolean;
  readonly indeterminate?: boolean;
  readonly onChange: (event: ChangeEvent<HTMLInputElement>) => void;
  readonly disabled?: boolean;
}

export function CheckboxCell({ checked, indeterminate = false, disabled = false, onChange }: CheckboxCellProps) {
  return (
    <div className={styles.checkbox_cell}>
      <Checkbox
        classNames={{
          root: styles.root,
        }}
        checked={checked}
        indeterminate={indeterminate}
        onChange={onChange}
        disabled={disabled}
      />
    </div>
  );
}
