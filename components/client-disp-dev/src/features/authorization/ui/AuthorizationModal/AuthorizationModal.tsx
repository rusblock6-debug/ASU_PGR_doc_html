import { useEffect } from 'react';
import { useForm } from 'react-hook-form';

import { hasValue } from '@/shared/lib/has-value';
import { AppButton } from '@/shared/ui/AppButton';
import { Modal } from '@/shared/ui/Modal';
import { PasswordInput } from '@/shared/ui/PasswordInput';
import { TextInput } from '@/shared/ui/TextInput';

import { useLogin } from '../../lib/hooks/useLogin';

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
 * Представляет компонент модального окна авторизации.
 */
export function AuthorizationModal(props: AuthorizationModalProps) {
  const { isOpen, onClose, onConfirm } = props;

  const [login, { isLoading }] = useLogin();

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
    clearErrors('root');
  };

  const onSubmit = async (data: FormState) => {
    try {
      await login({
        username: data.login,
        password: data.password,
      });

      onConfirm();
      onClose();
    } catch {
      setError('root', { type: 'manual', message: 'Неправильный логин или пароль' });
    }
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
                inputSize="md"
                variant="filled"
                labelPosition="vertical"
                {...register('login', { required: true, onChange: handleInputChange })}
              />
              <PasswordInput
                placeholder="Пароль"
                inputSize="md"
                variant="filled"
                labelPosition="vertical"
                {...register('password', { required: true, onChange: handleInputChange })}
              />
            </div>
            <p
              className={styles.error_text}
              data-visible={hasValue(errors.root)}
            >
              {errors.root?.message || '\u00A0'}
            </p>
          </div>
          <div className={styles.actions}>
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
