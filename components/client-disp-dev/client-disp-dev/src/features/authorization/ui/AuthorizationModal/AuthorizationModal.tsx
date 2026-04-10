import { TextInput, PasswordInput } from '@mantine/core';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';

import { AppButton } from '@/shared/ui/AppButton';
import { Modal } from '@/shared/ui/Modal';

import styles from './AuthorizationModal.module.css';

/**
 * Представляет свойства для модального окна авторизации.
 */
interface AuthorizationModalProps {
  /**
   * Возвращает состояние открытия.
   */
  readonly isOpen: boolean;
  /**
   * Возвращает делегат вызываемый при закрытии.
   */
  readonly onClose: () => void;
  /**
   * Возвращает делегат вызываемый при успешной авторизации.
   */
  readonly onConfirm: () => void;
}

/**
 * Представляет состояние формы авторизации.
 */
interface FormState {
  /**
   * Возвращает логин.
   */
  readonly login: string;
  /**
   * Возвращает пароль.
   */
  readonly password: string;
}

/**
 * Возвращает демонстрационные учетные данные для авторизации.
 */
const DEMO_AUTHORIZATION_CREDENTIALS = {
  login: 'admin',
  // eslint-disable-next-line sonarjs/no-hardcoded-passwords
  password: 'admin',
};

/**
 * Представляет компонент модального окна авторизации.
 */
export function AuthorizationModal(props: AuthorizationModalProps) {
  const { isOpen, onClose, onConfirm } = props;

  // Сделано для имитации процесса авторизации. Переделать при реализации функционала.
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty, isValid },
    setError,
    clearErrors,
    reset,
  } = useForm<FormState>({
    defaultValues: { login: '', password: '' },
    mode: 'onChange',
  });

  useEffect(() => {
    if (isOpen) {
      reset();
      clearErrors();
    }
  }, [isOpen, reset, clearErrors]);

  const handleInputChange = () => {
    if (errors.root) {
      clearErrors('root');
    }
  };

  const onSubmit = (data: FormState) => {
    // Таймер и изменение стейта сделано для имитации процесса авторизации. Переделать при реализации функционала.
    setIsLoading(true);

    setTimeout(() => {
      if (
        data.login === DEMO_AUTHORIZATION_CREDENTIALS.login &&
        data.password === DEMO_AUTHORIZATION_CREDENTIALS.password
      ) {
        onConfirm();
        onClose();
        localStorage.setItem('USER_LOGIN', data.login);
      } else {
        setError('root', { type: 'manual', message: 'Неправильный логин или пароль' });
      }

      setIsLoading(false);
    }, 1000);
  };

  const disabledSubmitButton = !isDirty || !isValid;

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      title={<p className={styles.title}>Авторизация</p>}
      centered
    >
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className={styles.root}>
          <div className={styles.content_container}>
            <div className={styles.inputs_container}>
              <TextInput
                placeholder="Логин"
                {...register('login', { required: true, onChange: handleInputChange })}
              />
              <PasswordInput
                placeholder="Пароль"
                {...register('password', { required: true, onChange: handleInputChange })}
              />
            </div>
            {errors.root && <p className={styles.error_text}>{errors.root.message}</p>}
          </div>
          <div>
            <AppButton
              type="submit"
              disabled={disabledSubmitButton}
              loading={isLoading}
              fullWidth
            >
              Войти
            </AppButton>
          </div>
        </div>
      </form>
    </Modal>
  );
}
