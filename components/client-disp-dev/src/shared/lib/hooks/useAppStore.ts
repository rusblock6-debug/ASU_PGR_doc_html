import { useStore } from 'react-redux';

/**
 * Типизированный хук для получения Redux store.
 * Позволяет читать актуальное состояние через `store.getState()` без подписки на обновления.
 *
 * @returns Типизированный Redux store
 */
export const useAppStore = () => useStore<RootState>();
