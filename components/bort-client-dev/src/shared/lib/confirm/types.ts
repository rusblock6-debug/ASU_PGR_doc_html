/** Опции диалога подтверждения действия. */
export interface ConfirmOptions {
  /** Заголовок модального окна. */
  readonly title?: string;
  /** Текст сообщения. */
  readonly message?: string;
  /** Текст кнопки подтверждения. */
  readonly confirmText?: string;
  /** Текст кнопки отмены. */
  readonly cancelText?: string;
  /** Размеры окна. */
  readonly size?: 'sm' | 'md';
}

/** Значение контекста confirm-провайдера. */
export interface ConfirmContextValue {
  confirm: (options: ConfirmOptions) => Promise<unknown>;
}
