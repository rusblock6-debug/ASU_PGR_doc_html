import type { Meta, StoryObj } from '@storybook/react-vite';

import { AppButton } from '../AppButton';

import { toast, ToastProvider } from './Toast';

const meta: Meta = {
  title: 'Shared/Toast',
  tags: ['autodocs'],
  decorators: [
    // eslint-disable-next-line @typescript-eslint/naming-convention
    (Story) => (
      <>
        <ToastProvider />
        <Story />
      </>
    ),
  ],
  parameters: {
    docs: {
      description: {
        component:
          'Система уведомлений на базе Mantine Notifications. Используйте объект `toast` для показа уведомлений.',
      },
    },
  },
};

export default meta;
type Story = StoryObj;

export const Success: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem' }}>
      <AppButton
        variant="secondary"
        onClick={() => toast.success({ message: 'Операция выполнена успешно' })}
      >
        Показать Toast
      </AppButton>
      <AppButton
        variant="secondary"
        onClick={() => toast.success({ message: 'Операция выполнена успешно', autoClose: false })}
      >
        Без автоскрытия
      </AppButton>
      <AppButton
        variant="secondary"
        onClick={() => toast.clean()}
      >
        Очистить все
      </AppButton>
    </div>
  ),
};

export const Warning: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem' }}>
      <AppButton
        variant="secondary"
        onClick={() => toast.warning({ message: 'Обратите внимание на это предупреждение' })}
      >
        Показать Toast
      </AppButton>
      <AppButton
        variant="secondary"
        onClick={() => toast.warning({ message: 'Обратите внимание на это предупреждение', autoClose: false })}
      >
        Без автоскрытия
      </AppButton>
      <AppButton
        variant="secondary"
        onClick={() => toast.clean()}
      >
        Очистить все
      </AppButton>
    </div>
  ),
};

export const Info: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem' }}>
      <AppButton
        variant="secondary"
        onClick={() => toast.info({ message: 'Это информационное сообщение для пользователя' })}
      >
        Показать Toast
      </AppButton>
      <AppButton
        variant="secondary"
        onClick={() => toast.info({ message: 'Это информационное сообщение для пользователя', autoClose: false })}
      >
        Без автоскрытия
      </AppButton>
      <AppButton
        variant="secondary"
        onClick={() => toast.clean()}
      >
        Очистить все
      </AppButton>
    </div>
  ),
};

export const ErrorToast: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem' }}>
      <AppButton
        variant="secondary"
        onClick={() => toast.error({ message: 'Произошла ошибка при выполнении операции' })}
      >
        Показать Toast
      </AppButton>
      <AppButton
        variant="secondary"
        onClick={() => toast.error({ message: 'Произошла ошибка при выполнении операции', autoClose: false })}
      >
        Без автоскрытия
      </AppButton>
      <AppButton
        variant="secondary"
        onClick={() => toast.clean()}
      >
        Очистить все
      </AppButton>
    </div>
  ),
};

export const LongMessage: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem' }}>
      <AppButton
        variant="secondary"
        onClick={() =>
          toast.info({
            message:
              'Это очень длинное сообщение, которое демонстрирует как toast справляется с большим количеством текста. Максимальная ширина ограничена 418px.',
          })
        }
      >
        Показать Toast
      </AppButton>
      <AppButton
        variant="secondary"
        onClick={() =>
          toast.info({
            message:
              'Это очень длинное сообщение, которое демонстрирует как toast справляется с большим количеством текста. Максимальная ширина ограничена 418px.',
            autoClose: false,
          })
        }
      >
        Без автоскрытия
      </AppButton>
      <AppButton
        variant="secondary"
        onClick={() => toast.clean()}
      >
        Очистить все
      </AppButton>
    </div>
  ),
};

export const AllTypesPlayground: StoryObj<{
  type: 'success' | 'warning' | 'info' | 'error' | 'promise';
  autoClose: number;
  message: string;
  promiseDelay: number;
  promiseResult: 'success' | 'error';
}> = {
  args: {
    type: 'success',
    autoClose: 3000,
    message: 'Текст уведомления',
    promiseDelay: 2000,
    promiseResult: 'success',
  },
  argTypes: {
    type: {
      control: 'select',
      options: ['success', 'warning', 'info', 'error', 'promise'],
      description: 'Тип уведомления',
    },
    autoClose: {
      control: { type: 'number', min: 0, max: 30000, step: 1000 },
      description: 'Время до скрытия в мс (0 = не скрывать)',
      if: { arg: 'type', neq: 'promise' },
    },
    message: {
      control: 'text',
      description: 'Текст сообщения',
      if: { arg: 'type', neq: 'promise' },
    },
    promiseDelay: {
      control: { type: 'number', min: 1000, max: 1000000, step: 1000 },
      description: 'Задержка Promise в мс',
      if: { arg: 'type', eq: 'promise' },
    },
    promiseResult: {
      control: 'select',
      options: ['success', 'error'],
      description: 'Результат Promise',
      if: { arg: 'type', eq: 'promise' },
    },
  },
  render: (args) => (
    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
      <AppButton
        variant="secondary"
        onClick={() => {
          if (args.type === 'promise') {
            const promise =
              args.promiseResult === 'success'
                ? new Promise((resolve) => setTimeout(() => resolve('done'), args.promiseDelay))
                : new Promise((_, reject) => setTimeout(() => reject(new Error('Failed')), args.promiseDelay));

            toast
              .promise(promise, {
                loading: { message: 'Загрузка...' },
                success: { message: 'Успешно завершено!' },
                error: { message: 'Произошла ошибка' },
              })
              .catch(() => {
                /* empty */
              });
          } else {
            toast[args.type]({
              message: args.message,
              autoClose: args.autoClose === 0 ? false : args.autoClose,
            });
          }
        }}
      >
        Показать Toast
      </AppButton>
      <AppButton
        variant="secondary"
        onClick={() => toast.clean()}
      >
        Очистить все
      </AppButton>
    </div>
  ),
};

export const AllTypes: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
      <AppButton
        variant="secondary"
        onClick={() => toast.success({ message: 'Для перехода в модуль требуется авторизация', autoClose: 10000 })}
      >
        Success
      </AppButton>
      <AppButton
        variant="secondary"
        onClick={() => toast.warning({ message: 'Для перехода в модуль требуется авторизация', autoClose: 10000 })}
      >
        Warning
      </AppButton>
      <AppButton
        variant="secondary"
        onClick={() => toast.info({ message: 'Для перехода в модуль требуется авторизация', autoClose: 10000 })}
      >
        Info
      </AppButton>
      <AppButton
        variant="secondary"
        onClick={() => toast.error({ message: 'Для перехода в модуль требуется авторизация', autoClose: 10000 })}
      >
        Error
      </AppButton>
      <AppButton
        variant="secondary"
        onClick={() => toast.clean()}
      >
        Очистить все
      </AppButton>
    </div>
  ),
};
