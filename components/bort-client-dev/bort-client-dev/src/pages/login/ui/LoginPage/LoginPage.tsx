import { useEffect, useRef, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';

import { ConfirmButton } from '@/widgets/kiosk-controls';

import { useAuth } from '@/shared/lib/auth';
import { cn } from '@/shared/lib/classnames-utils';
import { useKioskAside } from '@/shared/lib/kiosk-aside';
import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';
import { getRouteMain } from '@/shared/routes/router';

import styles from './LoginPage.module.css';

const KIOSK_FIELD_LOGIN = 'login-kiosk-login';
const KIOSK_FIELD_PASS = 'login-kiosk-pass-field';
const KIOSK_FIELD_SUBMIT = 'login-kiosk-submit';

/** Экран мок-входа (логин/пароль). */
export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const [loginValue, setLoginValue] = useState('');
  const [password, setPassword] = useState('');
  const [showError, setShowError] = useState(false);

  const formRef = useRef<HTMLFormElement>(null);
  const loginInputRef = useRef<HTMLInputElement>(null);
  const passwordInputRef = useRef<HTMLInputElement>(null);

  const { setItemIds, setOnConfirm, selectedId, setSelectedIndex } = useKioskNavigation();
  const { setAsideLeft } = useKioskAside();

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
        formRef.current?.requestSubmit();
      }
    });
    return () => {
      setOnConfirm(null);
    };
  }, [isAuthenticated, selectedId, setOnConfirm]);

  if (isAuthenticated) {
    return (
      <Navigate
        to={getRouteMain()}
        replace
      />
    );
  }

  const handleSubmit = (event: { preventDefault: () => void }) => {
    event.preventDefault();
    setShowError(false);
    const ok = login(loginValue, password);
    if (ok) {
      void navigate(getRouteMain(), { replace: true });
    } else {
      setShowError(true);
    }
  };

  const loginSelected = selectedId === KIOSK_FIELD_LOGIN;
  const passwordSelected = selectedId === KIOSK_FIELD_PASS;
  const submitSelected = selectedId === KIOSK_FIELD_SUBMIT;

  return (
    <div className={styles.page}>
      <form
        ref={formRef}
        className={styles.form}
        onSubmit={handleSubmit}
      >
        <div className={styles.fields_block}>
          <div className={styles.field}>
            <input
              ref={loginInputRef}
              autoComplete="username"
              placeholder="Логин"
              className={cn(
                styles.input,
                showError && styles.input_error,
                loginSelected && !showError && styles.input_selected,
              )}
              id="login-mock"
              name="login"
              onChange={(ev) => setLoginValue(ev.target.value)}
              onFocus={() => {
                setSelectedIndex(0);
              }}
              type="text"
              value={loginValue}
            />
          </div>
          <div className={styles.field}>
            <input
              ref={passwordInputRef}
              autoComplete="current-password"
              placeholder="Пароль"
              className={cn(
                styles.input,
                showError && styles.input_error,
                passwordSelected && !showError && styles.input_selected,
              )}
              id="password-mock"
              name="password"
              onChange={(ev) => setPassword(ev.target.value)}
              onFocus={() => {
                setSelectedIndex(1);
              }}
              type="password"
              value={password}
            />
          </div>
          {showError ? <p className={styles.error}>Неверный логин или пароль</p> : null}
        </div>
        <button
          className={cn(styles.submit, submitSelected && styles.submit_selected)}
          type="submit"
          onFocus={() => {
            setSelectedIndex(2);
          }}
        >
          ВОЙТИ
          <svg
            aria-hidden
            className={styles.arrow}
            viewBox="0 0 24 24"
          >
            <path
              d="M5 12h14m-6-6 6 6-6 6"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
            />
          </svg>
        </button>
      </form>
    </div>
  );
}
