import { cn } from '@/shared/lib/classnames-utils';
import { NO_DATA } from '@/shared/lib/constants';
import { hasValueNotEmpty } from '@/shared/lib/has-value';
import { mantineInput, mantineInputWrapper } from '@/shared/styles/mantine';

import styles from './ReadonlyField.module.css';

/**
 * Представляет свойства компонента {@link ReadonlyField}.
 */
interface ReadonlyFieldProps {
  /** Текст метки поля. */
  readonly label: string;
  /** Отображаемое значение. */
  readonly value: string | number | null;
  /** Дополнительный CSS-класс для корневого элемента. */
  readonly className?: string;
  /** Отображать маркер обязательного поля. */
  readonly withAsterisk?: boolean;
}

/**
 * Представляет компонент заглушки для инпутов c отображением значений, когда их нельзя редактировать.
 * Используется для оптимизации отрисовки, когда много заданий.
 */
export function ReadonlyField({ label, value, className, withAsterisk }: ReadonlyFieldProps) {
  return (
    <div
      className={cn(mantineInputWrapper.root, styles.root, className)}
      data-input-size="combobox-sm"
    >
      <span className={cn(mantineInputWrapper.label, styles.label)}>
        {label}
        {withAsterisk && <span className={mantineInputWrapper.required}> *</span>}
      </span>
      <span
        className={cn(mantineInput.input, mantineInputWrapper.input, styles.input)}
        data-variant="combobox-primary"
        data-disabled
        title={hasValueNotEmpty(value) ? String(value) : ''}
      >
        <span className={styles.value}>
          {hasValueNotEmpty(value) ? value : <span className={styles.placeholder}>{NO_DATA.LONG_DASH}</span>}
        </span>
      </span>
    </div>
  );
}
