import { useCallback } from 'react';
import { useDispatch } from 'react-redux';

import type { LoginRequest } from '@/shared/api/endpoints/auth';
import { useLoginMutation } from '@/shared/api/endpoints/auth';
import { authTokensReceived } from '@/shared/lib/auth-actions';

/**
 * Логин через RTK Query и запись токенов в auth-состояние.
 */
export const useLogin = () => {
  const dispatch = useDispatch();
  const [trigger, mutationResult] = useLoginMutation();

  const login = useCallback(
    async (arg: LoginRequest) => {
      const data = await trigger(arg).unwrap();
      dispatch(
        authTokensReceived({
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
        }),
      );
      return data;
    },
    [dispatch, trigger],
  );

  return [login, mutationResult] as const;
};
