import { createAction } from '@reduxjs/toolkit';

export const authTokensReceived = createAction<{ accessToken: string; refreshToken: string }>('auth/tokensReceived');

export const authLogout = createAction('auth/logout');

/**
 * Принудительно пересчитывает auth-состояние из переданных токенов.
 * Токены читаются в setupAuthStorageSync (при старте и из storage-события).
 */
export const authSyncFromStorage = createAction<{
  accessToken: string | null;
  refreshToken: string | null;
}>('auth/syncFromStorage');
