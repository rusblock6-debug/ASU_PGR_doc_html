import { createContext, useContext, useState } from 'react';

const SESSION_KEY = 'bort-auth';

const MOCK_USER = {
  login: 'zinoviev',
  // eslint-disable-next-line sonarjs/no-hardcoded-passwords -- мок для dev-демо
  password: '1234',
  displayName: 'Зиновьев Николай Иванович',
} as const;

/** Пользователь мок-сессии (отображаемое имя). */
export interface AuthUser {
  readonly displayName: string;
}

/** Значение React-контекста авторизации. */
interface AuthContextValue {
  readonly isAuthenticated: boolean;
  readonly user: AuthUser | null;
  readonly login: (username: string, password: string) => boolean;
  readonly logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Читает флаг сессии из `sessionStorage` (SSR-safe). */
function readStoredAuth(): boolean {
  if (typeof sessionStorage === 'undefined') {
    return false;
  }
  return sessionStorage.getItem(SESSION_KEY) === 'true';
}

/** Провайдер мок-авторизации (sessionStorage). */
export function AuthProvider({ children }: { readonly children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(readStoredAuth);

  const login = (username: string, password: string) => {
    const ok = username.trim() === MOCK_USER.login && password === MOCK_USER.password;
    if (ok) {
      sessionStorage.setItem(SESSION_KEY, 'true');
      setIsAuthenticated(true);
    }
    return ok;
  };

  const logout = () => {
    sessionStorage.removeItem(SESSION_KEY);
    setIsAuthenticated(false);
  };

  const value: AuthContextValue = {
    isAuthenticated,
    user: isAuthenticated ? { displayName: MOCK_USER.displayName } : null,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Доступ к мок-сессии (логин/логаут, пользователь). */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
