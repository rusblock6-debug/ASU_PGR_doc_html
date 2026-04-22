import { createSlice } from '@reduxjs/toolkit';

import type { JwtPayload, JwtPermission } from '@/shared/api/endpoints/auth';
import { authLogout, authSyncFromStorage, authTokensReceived } from '@/shared/lib/auth-actions';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';

import { decodeJwt } from '../lib/decode-jwt';

/** Состояние авторизации: пользователь из JWT и наличие refresh-токена. */
interface AuthState {
  /** Данные пользователя. */
  readonly user: JwtPayload | null;
  /** Наличие рефреш токена. */
  readonly hasRefreshToken: boolean;
}

/** Вычисляет AuthState по access/refresh токенам (валидность access по exp). */
const computeAuthState = (accessToken: string | null, refreshToken: string | null): AuthState => {
  const hasRefreshToken = hasValue(refreshToken);

  if (!hasValue(accessToken)) {
    return { user: null, hasRefreshToken };
  }

  try {
    const payload = decodeJwt(accessToken);
    const nowInSeconds = Math.floor(Date.now() / 1000);

    if (payload.exp > nowInSeconds || hasRefreshToken) {
      return { user: payload, hasRefreshToken };
    }

    return { user: null, hasRefreshToken };
  } catch {
    return { user: null, hasRefreshToken };
  }
};

const initialState: AuthState = { user: null, hasRefreshToken: false };

/**
 * Проверяет, изменился ли пользователь по id и exp.
 * Позволяет сохранить ссылочную стабильность state при повторных sync-диспатчах.
 */
const isSameUser = (prev: JwtPayload | null, next: JwtPayload | null) => {
  if (prev === next) return true;
  if (!prev || !next) return false;
  return prev.id === next.id && prev.exp === next.exp;
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(authTokensReceived, (_, { payload }) =>
      computeAuthState(payload.accessToken, payload.refreshToken),
    );

    builder.addCase(authSyncFromStorage, (state, { payload }) => {
      const next = computeAuthState(payload.accessToken, payload.refreshToken);

      if (isSameUser(state.user, next.user) && state.hasRefreshToken === next.hasRefreshToken) {
        return state;
      }

      return next;
    });

    builder.addCase(authLogout, () => ({ user: null, hasRefreshToken: false }));
  },
});

export const authReducer = authSlice.reducer;

export const selectIsAuthenticated = (state: RootState) => state.auth.user !== null || state.auth.hasRefreshToken;

export const selectUser = (state: RootState) => state.auth.user;

export const selectUserRoleName = (state: RootState) => state.auth.user?.role.name ?? null;

const EMPTY_PERMISSIONS: readonly JwtPermission[] = EMPTY_ARRAY;

export const selectUserPermissions = (state: RootState) => state.auth.user?.role.permissions ?? EMPTY_PERMISSIONS;
