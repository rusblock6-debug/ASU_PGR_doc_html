import { cn } from '@/shared/lib/classnames-utils';
import { AppButton } from '@/shared/ui/AppButton';
import { Modal } from '@/shared/ui/Modal';

import styles from './ConfirmModal.module.css';

/**
 * Представляет свойства для модального окна подтверждения.
 */
interface ConfirmModalProps {
  /** Возвращает состояние открытия. */
  readonly isOpen: boolean;
  /** Возвращает заголовок модального окна. */
  readonly title?: string;
  /** Возвращает текст сообщения. */
  readonly message?: string;
  /** Возвращает текст кнопки закрытия. */
  readonly closeButtonText?: string;
  /** Возвращает текст кнопки подтверждения. */
  readonly confirmButtonText?: string;
  /** Возвращает делегат вызываемый при закрытии. */
  readonly onClose: () => void;
  /** Возвращает делегат вызываемый в случае подтверждения выхода. */
  readonly onConfirm: () => void;
  /** Возвращает делегат вызываемый после завершения анимации закрытия. */
  readonly onTransitionEnd?: () => void;
  /** Возвращает состояние загрузки. */
  readonly isLoading?: boolean;
  /** Размеры окна. */
  readonly size?: 'sm' | 'md';
}

/**
 * Представляет компонент модального окна подтверждения.
 */
export function ConfirmModal(props: ConfirmModalProps) {
  const {
    isOpen,
    title,
    message,
    closeButtonText = 'Отмена',
    confirmButtonText = 'Подтвердить',
    size = 'sm',
    onClose,
    onConfirm,
    onTransitionEnd,
    isLoading,
  } = props;

  return (
    <Modal
      centered
      opened={isOpen}
      withCloseButton={false}
      title={<p className={styles.title}>{title}</p>}
      className={cn(styles.modal, styles.confirm_modal, {
        [styles.size_sm]: size === 'sm',
        [styles.size_md]: size === 'md',
      })}
      onClose={onClose}
      transitionProps={{ onExited: onTransitionEnd }}
    >
      <div className={styles.body}>
        <p className={styles.message}>{message}</p>
        <div className={styles.buttons}>
          <AppButton
            size="xl"
            variant="secondary"
            onClick={onClose}
            fullWidth
            disabled={isLoading}
          >
            {closeButtonText}
          </AppButton>
          <AppButton
            size="xl"
            onClick={onConfirm}
            fullWidth
            loading={isLoading}
          >
            {confirmButtonText}
          </AppButton>
        </div>
      </div>
    </Modal>
  );
}
