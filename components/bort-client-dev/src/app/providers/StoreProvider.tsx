import React from 'react';
import { Provider } from 'react-redux';

import { store } from '../store';

/** Пропсы провайдера Redux store. */
interface StoreProviderProps {
  readonly children: React.ReactNode;
}

/** Провайдер глобального Redux store. */
export function StoreProvider({ children }: StoreProviderProps) {
  return <Provider store={store}>{children}</Provider>;
}
