import type { NotificationData } from '@mantine/notifications';
import type { ReactNode } from 'react';

/** Тип уведомления, определяет цвет и иконку. */
export type ToastType = 'success' | 'warning' | 'info' | 'error';

/** Данные для типизированного тоста. */
export interface TypedToastData extends Omit<NotificationData, 'color'> {
  /** Элемент сообщения. */
  readonly message: ReactNode;
}

/**
 * Сообщения для тоста, отслеживающего состояние промиса.
 */
export interface PromiseToastMessages {
  /** Сообщение при успешном завершении. */
  readonly success: { title?: string; message: string };
  /** Сообщение во время выполнения промиса. */
  readonly loading?: { title?: string; message: string };
  /** Сообщение при ошибке. По умолчанию показывает текст ошибки. */
  readonly error?: { title?: string; message: string };
}
