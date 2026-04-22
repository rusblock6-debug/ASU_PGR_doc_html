import { type ChangeEvent, useEffect, useRef } from 'react';

import styles from './NativeCheckbox.module.css';

interface NativeCheckboxProps {
  readonly checked: boolean;
  readonly indeterminate?: boolean;
  readonly onChange: (event: ChangeEvent<HTMLInputElement>) => void;
  readonly disabled?: boolean;
}

/**
 * Нативный чекбокс с поддержкой indeterminate состояния
 *
 * Причина создания:
 * По каким-то причинам компонент Checkbox из @mantine/core некорректно обрабатывает ситуацию, когда в таблице выбраны все элементы.
 * В этом случае Mantine игнорирует значение checked и не показывает галочку, даже если все строки выбраны.
 */
export function NativeCheckbox({ checked, indeterminate = false, disabled = false, onChange }: NativeCheckboxProps) {
  const checkboxRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (checkboxRef.current) {
      checkboxRef.current.indeterminate = indeterminate;
    }
  }, [indeterminate]);

  return (
    <div className={styles.wrapper}>
      <input
        ref={checkboxRef}
        type="checkbox"
        className={styles.checkbox}
        checked={checked}
        onChange={onChange}
        disabled={disabled}
      />
      <svg
        className={styles.icon}
        viewBox="0 0 10 7"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M4 4.586L1.707 2.293A1 1 0 1 0 .293 3.707l3 3a.997.997 0 0 0 1.414 0l5-5A1 1 0 1 0 8.293.293L4 4.586z"
          fill="currentColor"
          fillRule="evenodd"
          clipRule="evenodd"
        />
      </svg>
      <svg
        className={styles.indeterminate_icon}
        viewBox="0 0 10 2"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M0 1h10"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
}
