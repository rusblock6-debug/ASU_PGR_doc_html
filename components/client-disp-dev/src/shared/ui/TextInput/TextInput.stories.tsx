import type { Meta, StoryObj } from '@storybook/react-vite';

import { TextInput } from './TextInput';

const meta: Meta<typeof TextInput> = {
  title: 'Shared/TextInput',
  component: TextInput,
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['default', 'unstyled', 'filled', 'outline', 'combobox-primary'],
      description: 'Вариант поля ввода',
    },
    inputSize: {
      control: 'select',
      options: ['xs', 'sm', 'md', 'lg', 'combobox-sm'],
      description: 'Размер поля ввода',
    },
    labelPosition: {
      control: 'select',
      options: ['horizontal', 'vertical'],
      description: 'Позиция метки относительно поля',
    },
    disabled: {
      control: 'boolean',
      description: 'Отключено ли поле',
    },
    placeholder: {
      control: 'text',
      description: 'Placeholder',
    },
    label: {
      control: 'text',
      description: 'Метка поля',
    },
    error: {
      control: 'text',
      description: 'Текст ошибки',
    },
    description: {
      control: 'text',
      description: 'Описание поля',
    },
    withAsterisk: {
      control: 'boolean',
      description: 'Показывать ли звездочку для обязательного поля',
    },
    clearable: {
      control: 'boolean',
      description: 'Показывать ли кнопку очистки',
    },
    withArrow: {
      control: 'boolean',
      description: 'Показывать ли стрелку (для select-подобных компонентов)',
    },
    arrowRotated: {
      control: 'boolean',
      description: 'Повернута ли стрелка',
    },
  },
  args: {
    variant: 'default',
    inputSize: 'xs',
    placeholder: 'Введите текст...',
  },
};

export default meta;
type Story = StoryObj<typeof TextInput>;

export const Default: Story = {
  args: {
    variant: 'default',
    inputSize: 'xs',
    labelPosition: 'horizontal',
    placeholder: 'Введите текст...',
    disabled: false,
    label: '',
    error: '',
    description: '',
    withAsterisk: false,
    clearable: false,
    withArrow: false,
    arrowRotated: false,
    required: false,
    readOnly: false,
  },
};

export const WithError: Story = {
  args: {
    variant: 'default',
    inputSize: 'xs',
    label: 'Поле с ошибкой',
    error: 'Это поле обязательно для заполнения',
    placeholder: 'Введите текст...',
  },
};

export const AllSizes: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '400px' }}>
      <div>
        <p style={{ marginBottom: '8px', color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>Size XS</p>
        <TextInput
          variant="default"
          inputSize="xs"
          placeholder="Size XS"
        />
      </div>

      <div>
        <p style={{ marginBottom: '8px', color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>Size SM</p>
        <TextInput
          variant="default"
          inputSize="sm"
          placeholder="Size SM"
        />
      </div>

      <div>
        <p style={{ marginBottom: '8px', color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>Size MD</p>
        <TextInput
          variant="default"
          inputSize="md"
          placeholder="Size MD"
        />
      </div>

      <div>
        <p style={{ marginBottom: '8px', color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>Size LG</p>
        <TextInput
          variant="default"
          inputSize="lg"
          placeholder="Size LG"
        />
      </div>
    </div>
  ),
};

export const AllSizesWithError: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '400px' }}>
      <div>
        <p style={{ marginBottom: '8px', color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          Size XS с ошибкой
        </p>
        <TextInput
          variant="default"
          inputSize="xs"
          label="Поле ввода"
          error="Ошибка валидации"
          placeholder="Size XS"
          withAsterisk
        />
      </div>

      <div>
        <p style={{ marginBottom: '8px', color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          Size SM с ошибкой
        </p>
        <TextInput
          variant="default"
          inputSize="sm"
          label="Поле ввода"
          error="Ошибка валидации"
          placeholder="Size SM"
          withAsterisk
        />
      </div>

      <div>
        <p style={{ marginBottom: '8px', color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          Size MD с ошибкой
        </p>
        <TextInput
          variant="default"
          inputSize="md"
          label="Поле ввода"
          error="Ошибка валидации"
          placeholder="Size MD"
          withAsterisk
        />
      </div>

      <div>
        <p style={{ marginBottom: '8px', color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          Size LG с ошибкой
        </p>
        <TextInput
          variant="default"
          inputSize="lg"
          label="Поле ввода"
          error="Ошибка валидации"
          placeholder="Size LG"
          withAsterisk
        />
      </div>
    </div>
  ),
};

export const Disabled: Story = {
  args: {
    variant: 'default',
    inputSize: 'xs',
    disabled: true,
    defaultValue: 'Отключенное поле',
  },
};

export const FilledVariant: Story = {
  args: {
    variant: 'filled',
    inputSize: 'xs',
    placeholder: 'Введите текст...',
  },
};

export const AllSizesFilled: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '400px' }}>
      <div>
        <p style={{ marginBottom: '8px', color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          Size XS (filled)
        </p>
        <TextInput
          variant="filled"
          inputSize="xs"
          placeholder="Size XS"
        />
      </div>

      <div>
        <p style={{ marginBottom: '8px', color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          Size SM (filled)
        </p>
        <TextInput
          variant="filled"
          inputSize="sm"
          placeholder="Size SM"
        />
      </div>

      <div>
        <p style={{ marginBottom: '8px', color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          Size MD (filled)
        </p>
        <TextInput
          variant="filled"
          inputSize="md"
          placeholder="Size MD"
        />
      </div>

      <div>
        <p style={{ marginBottom: '8px', color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          Size LG (filled)
        </p>
        <TextInput
          variant="filled"
          inputSize="lg"
          placeholder="Size LG"
        />
      </div>
    </div>
  ),
};

export const FilledWithError: Story = {
  args: {
    variant: 'filled',
    inputSize: 'xs',
    label: 'Поле с ошибкой',
    error: 'Это поле обязательно для заполнения',
    placeholder: 'Введите текст...',
  },
};

export const Clearable: Story = {
  args: {
    variant: 'default',
    inputSize: 'xs',
    label: 'Поле с очисткой',
    placeholder: 'Введите текст...',
    clearable: true,
    defaultValue: 'Текст для очистки',
  },
};

export const WithArrow: Story = {
  args: {
    variant: 'default',
    inputSize: 'xs',
    label: 'Поле со стрелкой',
    placeholder: 'Выберите значение...',
    withArrow: true,
  },
};

export const WithArrowRotated: Story = {
  args: {
    variant: 'default',
    inputSize: 'xs',
    label: 'Поле с повернутой стрелкой',
    placeholder: 'Выберите значение...',
    withArrow: true,
    arrowRotated: true,
  },
};

export const HorizontalLabel: Story = {
  args: {
    variant: 'default',
    inputSize: 'xs',
    label: 'Горизонтальная метка',
    labelPosition: 'horizontal',
    placeholder: 'Введите текст...',
  },
};

export const VerticalLabel: Story = {
  args: {
    variant: 'default',
    inputSize: 'xs',
    label: 'Вертикальная метка',
    labelPosition: 'vertical',
    placeholder: 'Введите текст...',
  },
};

export const Combobox: Story = {
  args: {
    variant: 'combobox-primary',
    inputSize: 'combobox-sm',
    label: 'Вертикальная метка',
    labelPosition: 'vertical',
    placeholder: 'Введите текст...',
    required: true,
  },
};
