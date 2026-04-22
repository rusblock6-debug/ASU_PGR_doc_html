/** Ключ access token в `localStorage`. */
const ACCESS_TOKEN_KEY = 'asu-gtk-access_token';
/** Ключ refresh token в `localStorage`. */
const REFRESH_TOKEN_KEY = 'asu-gtk-refresh_token';

export const tokenStorage = {
  /** Ключ access token в `localStorage`. */
  ACCESS_TOKEN_KEY,
  /** Ключ refresh token в `localStorage`. */
  REFRESH_TOKEN_KEY,

  /** Возвращает access token из `localStorage` (или `null`). */
  getAccessToken: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  /** Возвращает refresh token из `localStorage` (или `null`). */
  getRefreshToken: () => localStorage.getItem(REFRESH_TOKEN_KEY),

  /** Проверяет наличие access token в `localStorage`. */
  hasAccessToken: () => Boolean(localStorage.getItem(ACCESS_TOKEN_KEY)),
  /** Проверяет наличие refresh token в `localStorage`. */
  hasRefreshToken: () => Boolean(localStorage.getItem(REFRESH_TOKEN_KEY)),

  /**
   * Сохраняет пару токенов в `localStorage`.
   */
  setTokens: (accessToken: string, refreshToken: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },

  /**
   * Удаляет токены из `localStorage`.
   */
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
} as const;
