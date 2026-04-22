import { type TypedUseSelectorHook, useSelector } from 'react-redux';

/**
 * Типизированный хук для выборки данных из Redux store.
 * Гарантирует корректный вывод типов для селекторов на основе RootState.
 *
 * @returns Значение из store, возвращаемое переданным селектором
 */
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
