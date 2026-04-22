import { createContext, useContext, useState, type ReactNode } from 'react';

import { NO_DATA } from '@/shared/lib/constants';

/**
 * Информация для центральной части kiosk-шапки.
 */
export interface KioskHeaderInfo {
  readonly locationLabel: string;
  readonly locationSubLabel?: string;
}

/**
 * Контракт контекста для чтения/обновления данных шапки.
 */
interface KioskHeaderInfoContextValue {
  readonly headerInfo: KioskHeaderInfo;
  readonly setHeaderInfo: (next: KioskHeaderInfo) => void;
}

const DEFAULT_HEADER_INFO: KioskHeaderInfo = {
  locationLabel: NO_DATA.LONG_DASH,
};

const KioskHeaderInfoContext = createContext<KioskHeaderInfoContextValue | null>(null);

/**
 * Пропсы провайдера контекста шапки.
 */
interface KioskHeaderInfoProviderProps {
  readonly children: ReactNode;
}

/**
 * Провайдер состояния шапки kiosk-интерфейса.
 */
export const KioskHeaderInfoProvider = ({ children }: KioskHeaderInfoProviderProps) => {
  const [headerInfo, setHeaderInfoState] = useState<KioskHeaderInfo>(DEFAULT_HEADER_INFO);

  const setHeaderInfo = (next: KioskHeaderInfo) => {
    setHeaderInfoState(next);
  };

  const value: KioskHeaderInfoContextValue = {
    headerInfo,
    setHeaderInfo,
  };

  return <KioskHeaderInfoContext.Provider value={value}>{children}</KioskHeaderInfoContext.Provider>;
};

/**
 * Хук доступа к данным kiosk-шапки.
 */
export const useKioskHeaderInfo = () => {
  const context = useContext(KioskHeaderInfoContext);
  if (!context) {
    throw new Error('useKioskHeaderInfo must be used within KioskHeaderInfoProvider');
  }
  return context;
};
