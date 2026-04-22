import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

/** Значение контекста боковых панелей kiosk-лейаута. */
interface KioskAsideContextValue {
  readonly asideLeft: ReactNode | null;
  readonly asideRight: ReactNode | null;
  readonly asideLeftWidth: string | null;
  readonly asideRightWidth: string | null;
  readonly setAsideLeft: (node: ReactNode | null) => void;
  readonly setAsideRight: (node: ReactNode | null) => void;
  readonly setAsideLeftWidth: (width: string | null) => void;
  readonly setAsideRightWidth: (width: string | null) => void;
}

/** Пропсы провайдера боковых панелей. */
interface KioskAsideProviderProps {
  readonly children: ReactNode;
}

const KioskAsideContext = createContext<KioskAsideContextValue | null>(null);

/** Провайдер состояния левой и правой aside-панелей kiosk-лейаута. */
export const KioskAsideProvider = ({ children }: KioskAsideProviderProps) => {
  const [asideLeft, setAsideLeftState] = useState<ReactNode | null>(null);
  const [asideRight, setAsideRightState] = useState<ReactNode | null>(null);
  const [asideLeftWidth, setAsideLeftWidthState] = useState<string | null>(null);
  const [asideRightWidth, setAsideRightWidthState] = useState<string | null>(null);

  const setAsideLeft = useCallback((node: ReactNode | null) => {
    setAsideLeftState(node);
  }, []);

  const setAsideRight = useCallback((node: ReactNode | null) => {
    setAsideRightState(node);
  }, []);

  const setAsideLeftWidth = useCallback((width: string | null) => {
    setAsideLeftWidthState(width);
  }, []);

  const setAsideRightWidth = useCallback((width: string | null) => {
    setAsideRightWidthState(width);
  }, []);

  const value: KioskAsideContextValue = useMemo(
    () => ({
      asideLeft,
      asideRight,
      asideLeftWidth,
      asideRightWidth,
      setAsideLeft,
      setAsideRight,
      setAsideLeftWidth,
      setAsideRightWidth,
    }),
    [
      asideLeft,
      asideRight,
      asideLeftWidth,
      asideRightWidth,
      setAsideLeft,
      setAsideRight,
      setAsideLeftWidth,
      setAsideRightWidth,
    ],
  );

  return <KioskAsideContext.Provider value={value}>{children}</KioskAsideContext.Provider>;
};

/** Доступ к aside-панелям kiosk-лейаута (left/right + ширина). */
export const useKioskAside = () => {
  const context = useContext(KioskAsideContext);

  if (!context) {
    throw new Error('useKioskAside must be used within KioskAsideProvider');
  }

  return context;
};
