import type { PropsWithChildren } from 'react';
import { createContext, useCallback, useContext, useMemo, useRef } from 'react';

type ResizeListener = () => void;

/**
 * Представляет значение контекста компонента группы элементов с изменяемыми размерами.
 */
interface ResizeContextValue {
  /** Возвращает обработчик изменения размера. */
  readonly notifyResize: () => void;
  /** Возвращает функцию подписки на изменения размера. */
  readonly subscribe: (listener: ResizeListener) => () => void;
}

const ResizeContext = createContext<ResizeContextValue | null>(null);

/**
 * Представляет провайдер контекста компонента группы элементов с изменяемыми размерами.
 */
export function ResizeProvider({ children }: Readonly<PropsWithChildren>) {
  const listenersRef = useRef<Set<ResizeListener>>(new Set());

  const subscribe = useCallback((listener: ResizeListener) => {
    listenersRef.current.add(listener);

    return () => {
      listenersRef.current.delete(listener);
    };
  }, []);

  const notifyResize = useCallback(() => {
    listenersRef.current.forEach((listener) => {
      listener();
    });
  }, []);

  const value = useMemo(
    () => ({
      notifyResize,
      subscribe,
    }),
    [notifyResize, subscribe],
  );

  return <ResizeContext.Provider value={value}>{children}</ResizeContext.Provider>;
}

/**
 * Возвращает хук контекста {@link ResizeContext}.
 */
export function useResizeContext() {
  const context = useContext(ResizeContext);

  if (!context) {
    throw new Error('useResizeContext must be used within ResizeProvider');
  }

  return context;
}
