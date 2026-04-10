import React from 'react';
import { Provider } from 'react-redux';

import { store } from '../store';

interface StoreProviderProps {
  readonly children: React.ReactNode;
}

export function StoreProvider({ children }: StoreProviderProps) {
  return <Provider store={store}>{children}</Provider>;
}
