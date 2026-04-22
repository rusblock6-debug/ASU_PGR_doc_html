import { rtkApi } from '@/shared/api';

/**
 * Данные для логина.
 */
export interface LoginRequest {
  /** Логин пользователя. */
  readonly username: string;
  /** Пароль пользователя. */
  readonly password: string;
}

/**
 * Токены, возвращаемые backend после успешной аутентификации.
 */
export interface TokenResponse {
  /** Access token. */
  readonly access_token: string;
  /** Refresh token. */
  readonly refresh_token: string;
}

/**
 * RTK Query endpoints для авторизации.
 */
export const authRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    /**
     * Логин: возвращает пару токенов.
     */
    login: build.mutation<TokenResponse, LoginRequest>({
      query: (body) => ({
        url: '/v1/auth/login',
        method: 'POST',
        body,
      }),
      extraOptions: {
        skipReauth: true,
      },
    }),

    /**
     * Логаут: инвалидирует refresh token (если он есть).
     */
    logout: build.mutation<void, { refreshToken: string | null }>({
      query: ({ refreshToken }) => ({
        url: '/v1/auth/logout',
        method: 'POST',
        body: refreshToken ? { refresh_token: refreshToken } : undefined,
      }),
    }),
  }),
});

/** RTK Query hooks для login/logout. */
export const { useLoginMutation, useLogoutMutation } = authRtkApi;
