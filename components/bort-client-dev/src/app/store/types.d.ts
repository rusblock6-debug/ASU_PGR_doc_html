import type { store } from './index';

/**
 * Глобальные типы для Redux Store.
 * Чтобы использовать в shared слое без нарушения принципов FSD
 */
declare global {
  /**
   * Тип состояния всего приложения Redux
   */
  type RootState = ReturnType<typeof store.getState>;

  /**
   * Тип dispatch функции для Redux store
   */
  type AppDispatch = typeof store.dispatch;
}

export {};
