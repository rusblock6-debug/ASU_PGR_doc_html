import { useCallback, useEffect, useRef } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';

import { ConfirmButton } from '@/widgets/kiosk-controls';

import ArrowRightIcon from '@/shared/assets/icons/ic-arrow-right.svg?react';
import { useAuth } from '@/shared/lib/auth';
import { cn } from '@/shared/lib/classnames-utils';
import { useAppForm } from '@/shared/lib/forms';
import { useKioskAside } from '@/shared/lib/kiosk-aside';
import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';
import { getRouteMain } from '@/shared/routes/router';
import { FormField } from '@/shared/ui/FormField';
import { FormInput } from '@/shared/ui/FormInput';

import { loginFormSchema, type LoginFormValues } from './login-schema';
import styles from './LoginPage.module.css';

const KIOSK_FIELD_LOGIN = 'login-kiosk-login';
const KIOSK_FIELD_PASS = 'login-kiosk-pass-field';
const KIOSK_FIELD_SUBMIT = 'login-kiosk-submit';

/** Экран мок-входа (логин/пароль). */
export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();

  const loginInputRef = useRef<HTMLInputElement>(null);
  const passwordInputRef = useRef<HTMLInputElement>(null);

  const { setItemIds, setOnConfirm, selectedId, setSelectedIndex } = useKioskNavigation();
  const { setAsideLeft } = useKioskAside();

  const {
    control,
    handleSubmit,
    setError,
    clearErrors,
    formState: { errors },
  } = useAppForm(loginFormSchema, {
    defaultValues: { login: '', password: '' },
  });

  const onValidSubmit = useCallback(
    (values: LoginFormValues) => {
      clearErrors('root');
      const ok = login(values.login, values.password);
      if (ok) {
        void navigate(getRouteMain(), { replace: true });
      } else {
        setError('root', { message: 'Неверный логин или пароль' });
      }
    },
    [clearErrors, login, navigate, setError],
  );

  useEffect(() => {
    if (isAuthenticated) {
      return;
    }
    setItemIds([KIOSK_FIELD_LOGIN, KIOSK_FIELD_PASS, KIOSK_FIELD_SUBMIT]);
    return () => {
      setItemIds([]);
    };
  }, [isAuthenticated, setItemIds]);

  useEffect(() => {
    if (isAuthenticated) {
      return;
    }
    setAsideLeft(<ConfirmButton />);
    return () => {
      setAsideLeft(null);
    };
  }, [isAuthenticated, setAsideLeft]);

  useEffect(() => {
    if (isAuthenticated) {
      return;
    }
    setOnConfirm(() => {
      if (selectedId === KIOSK_FIELD_LOGIN) {
        loginInputRef.current?.focus();
        return;
      }
      if (selectedId === KIOSK_FIELD_PASS) {
        passwordInputRef.current?.focus();
        return;
      }
      if (selectedId === KIOSK_FIELD_SUBMIT) {
        void handleSubmit(onValidSubmit)();
      }
    });
    return () => {
      setOnConfirm(null);
    };
  }, [handleSubmit, isAuthenticated, onValidSubmit, selectedId, setOnConfirm]);

  if (isAuthenticated) {
    return (
      <Navigate
        to={getRouteMain()}
        replace
      />
    );
  }

  const loginSelected = selectedId === KIOSK_FIELD_LOGIN;
  const passwordSelected = selectedId === KIOSK_FIELD_PASS;
  const submitSelected = selectedId === KIOSK_FIELD_SUBMIT;

  const showFieldErrorStyle = Boolean(errors.root);

  return (
    <div className={styles.page}>
      <form
        className={styles.form}
        onSubmit={handleSubmit(onValidSubmit)}
      >
        <div className={styles.fields_block}>
          <FormField
            className={styles.field}
            error={errors.login}
          >
            <FormInput<LoginFormValues>
              autoComplete="username"
              control={control}
              hasError={Boolean(errors.login) || showFieldErrorStyle}
              id="login-mock"
              inputRef={loginInputRef}
              name="login"
              onFocus={() => {
                setSelectedIndex(0);
              }}
              placeholder="Логин"
              selected={loginSelected && !errors.login && !showFieldErrorStyle}
              type="text"
            />
          </FormField>
          <FormField
            className={styles.field}
            error={errors.password}
          >
            <FormInput<LoginFormValues>
              autoComplete="current-password"
              control={control}
              hasError={Boolean(errors.password) || showFieldErrorStyle}
              id="password-mock"
              inputRef={passwordInputRef}
              name="password"
              onFocus={() => {
                setSelectedIndex(1);
              }}
              placeholder="Пароль"
              selected={passwordSelected && !errors.password && !showFieldErrorStyle}
              type="password"
            />
          </FormField>
          {errors.root?.message ? <p className={styles.error}>{errors.root.message}</p> : null}
        </div>
        <button
          className={cn(styles.submit, submitSelected && styles.submit_selected)}
          type="submit"
          onFocus={() => {
            setSelectedIndex(2);
          }}
        >
          ВОЙТИ
          <ArrowRightIcon
            className={styles.arrow}
            aria-hidden
          />
        </button>
      </form>
    </div>
  );
}
