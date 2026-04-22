import type { JwtPayload } from '@/shared/api/endpoints/auth';

/**
 * Декодирует JWT payload без валидации подписи.
 */
export const decodeJwt = (token: string) => {
  const [, payload] = token.split('.');

  if (!payload) {
    throw new Error('Invalid JWT: missing payload');
  }

  const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '=');

  const json = atob(padded);

  return JSON.parse(json) as JwtPayload;
};
