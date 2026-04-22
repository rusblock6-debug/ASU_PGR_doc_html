import { useDispatch } from 'react-redux';

/**
 * Типизированный хук для получения функции dispatch из Redux store.
 * Гарантирует корректные типы для экшенов при использовании в компонентах.
 *
 * @returns Функция dispatch приложения (AppDispatch)
 */
export const useAppDispatch = () => useDispatch<AppDispatch>();
