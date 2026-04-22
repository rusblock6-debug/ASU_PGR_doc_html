import type { ModalProps as MantineModalProps } from '@mantine/core';
import { Modal as MantineModal } from '@mantine/core';

import { cn } from '@/shared/lib/classnames-utils';

import styles from './Modal.module.css';

/**
 * Представляет компонент модального окна.
 */
export function Modal(props: Readonly<MantineModalProps>) {
  const { className, classNames: propsClassNames, transitionProps: propsTransitionProps, ...restProps } = props;

  return (
    <MantineModal
      {...restProps}
      className={cn(styles.modal, className)}
      classNames={{
        content: styles.modal_content,
        header: styles.modal_header,
        overlay: styles.modal_overlay,
        inner: styles.modal_inner,
        ...propsClassNames,
      }}
      overlayProps={{
        backgroundOpacity: 0.28,
        color: '#999999',
        blur: 6,
      }}
      transitionProps={{
        duration: 200,
        transition: 'fade-down',
        ...propsTransitionProps,
      }}
    />
  );
}
