import { Notifications, notifications } from '@mantine/notifications';

import { cn } from '@/shared/lib/classnames-utils';
import { Z_INDEX } from '@/shared/lib/constants';

import ErrorIcon from './assets/error.svg?react';
import InfoIcon from './assets/info.svg?react';
import SuccessIcon from './assets/success.svg?react';
import WarningIcon from './assets/warning.svg?react';
import styles from './Toast.module.css';
import type { PromiseToastMessages, ToastType, TypedToastData } from './types';

const AUTO_CLOSE_DELAY = 3_000;

/**
 * API для работы с уведомлениями. Подробнее https://mantine.dev/x/notifications/.
 */
export const toast = {
  /**
   * Показать уведомление с загрузкой, затем обновить на успех/ошибку.
   */
  promise: showLoader,
  /**
   * Показать success уведомление (зеленый).
   */
  success: (data: TypedToastData) => showTyped('success', data),
  /**
   * Показать warning уведомление (желтый).
   */
  warning: (data: TypedToastData) => showTyped('warning', data),
  /**
   * Показать info уведомление (белый).
   */
  info: (data: TypedToastData) => showTyped('info', data),
  /**
   * Показать error уведомление (красный).
   */
  error: (data: TypedToastData) => showTyped('error', data),
  /**
   * Скрыть уведомление по id.
   */
  hide: (id: string) => notifications.hide(id),
  /**
   * Очистить все уведомления.
   */
  clean: () => notifications.clean(),
  /**
   * Очистить очередь уведомлений.
   */
  cleanQueue: () => notifications.cleanQueue(),
};

/**
 * Провайдер для системы уведомлений (toast).
 */
export function ToastProvider() {
  return (
    <Notifications
      position="bottom-right"
      autoClose={AUTO_CLOSE_DELAY}
      limit={5}
      zIndex={Z_INDEX.MODAL_BACKDROP}
      className={styles.toast}
      classNames={{
        root: styles.root,
      }}
    />
  );
}

const typeStyles = {
  success: styles.success,
  warning: styles.warning,
  info: styles.info,
  error: styles.error,
};

const typeIcons = {
  success: <SuccessIcon />,
  warning: <WarningIcon />,
  info: <InfoIcon />,
  error: <ErrorIcon />,
};

const notificationClassNames = {
  root: styles.notification,
  title: styles.title,
  description: styles.description,
  icon: styles.icon,
  loader: styles.loader,
};

function showTyped(type: ToastType, data: TypedToastData) {
  return notifications.show({
    withCloseButton: false,
    icon: typeIcons[type],
    ...data,
    classNames: {
      ...notificationClassNames,
      root: cn(styles.notification, typeStyles[type]),
    },
  });
}

function updateTyped(type: ToastType, data: TypedToastData & { id: string }) {
  return notifications.update({
    withCloseButton: false,
    icon: typeIcons[type],
    ...data,
    classNames: {
      ...notificationClassNames,
      root: cn(styles.notification, typeStyles[type]),
    },
  });
}

async function showLoader<T>(promise: Promise<T>, messages: PromiseToastMessages): Promise<T> {
  const id = toast.info({
    loading: true,
    title: messages.loading?.title,
    message: messages.loading?.message,
    autoClose: false,
  });

  const errorMessage = messages.error ?? { message: 'Произошла ошибка' };

  try {
    const result = await promise;
    updateTyped('success', {
      id,
      loading: false,
      title: messages.success.title,
      message: messages.success.message,
      autoClose: AUTO_CLOSE_DELAY,
    });
    return result;
  } catch (error) {
    updateTyped('error', {
      id,
      loading: false,
      title: errorMessage.title,
      message: errorMessage.message,
      autoClose: AUTO_CLOSE_DELAY,
    });
    throw error;
  }
}
