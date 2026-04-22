import CrossIcon from '@/shared/assets/icons/ic-cross.svg?react';
import { AppButton } from '@/shared/ui/AppButton';

import styles from './FormHeader.module.css';

/** Представляет свойства компонента верхней панели формы. */
interface FormHeaderProps {
  /** Возвращает заголовок. */
  readonly title: string;
  /** Возвращает делегат, вызываемый при закрытии панели. */
  readonly onClose: () => void;
}

/**
 * Представляет компонент верхней панели формы.
 */
export function FormHeader({ title, onClose }: FormHeaderProps) {
  return (
    <div className={styles.header}>
      <p className={styles.title}>{title}</p>
      <AppButton
        onlyIcon
        size="s"
        variant="clear"
        onClick={onClose}
      >
        <CrossIcon className={styles.close_icon} />
      </AppButton>
    </div>
  );
}
