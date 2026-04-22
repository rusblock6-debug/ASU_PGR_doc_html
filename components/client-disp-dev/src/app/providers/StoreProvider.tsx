import { type PropsWithChildren } from 'react';
import { Provider } from 'react-redux';

import { store } from '../store';

/** Оборачивает дерево в Redux `Provider` с корневым `store` приложения. */
export function StoreProvider({ children }: Readonly<PropsWithChildren>) {
  return <Provider store={store}>{children}</Provider>;
}
