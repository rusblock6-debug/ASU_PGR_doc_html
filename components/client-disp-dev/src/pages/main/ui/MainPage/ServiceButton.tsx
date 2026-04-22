import { cn } from '@/shared/lib/classnames-utils';

import styles from './ServiceButton.module.css';

type ServiceButtonVariant = 'pgr' | 'clone' | 'orem' | 'asodu' | 'vgok' | 'learning';

/**
 * Свойства компонента кнопки {@link ServiceButton}.
 */
interface ServiceButtonProps {
  /** Визуальный вариант кнопки (определяет фоновое изображение). */
  readonly variant: ServiceButtonVariant;
  /** Обработчик клика для перехода к модулю. */
  readonly handleModuleClick: () => void;
  /** Название сервиса. */
  readonly title: string;
  /** Краткое описание сервиса. */
  readonly description: string;
}

/**
 * Кнопка перехода к определенному приложению на маркетинговой странице.
 */
export function ServiceButton({ variant, handleModuleClick, title, description }: ServiceButtonProps) {
  return (
    <button
      className={cn(styles.button, styles[variant])}
      onClick={handleModuleClick}
      type="button"
    >
      <p className={styles.button_title}>{title}</p>
      <p className={styles.button_description}>{description}</p>
    </button>
  );
}
