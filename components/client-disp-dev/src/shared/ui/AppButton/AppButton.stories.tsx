import type { Meta, StoryObj } from '@storybook/react-vite';

import DummyIcon from '@/shared/assets/icons/dummy.svg?react';

import { AppButton } from './AppButton';

const meta: Meta<typeof AppButton> = {
  title: 'Shared/AppButton',
  component: AppButton,
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['primary', 'secondary', 'clear'],
      description: 'Вариант кнопки',
    },
    size: {
      control: 'select',
      options: ['l', 'm', 's', 'xs'],
      description: 'Размер кнопки',
    },
    disabled: {
      control: 'boolean',
      description: 'Отключена ли кнопка',
    },
    loading: {
      control: 'boolean',
      description: 'Состояние загрузки',
    },
  },
  args: {
    children: 'Кнопка',
  },
};

export default meta;
type Story = StoryObj<typeof AppButton>;

export const Primary: Story = {
  args: {
    variant: 'primary',
    size: 'm',
  },
};

export const PrimaryLarge: Story = {
  args: {
    variant: 'primary',
    size: 'l',
    children: 'Кнопка',
  },
};

export const Secondary: Story = {
  args: {
    variant: 'secondary',
    size: 'm',
  },
};

export const SecondaryLarge: Story = {
  args: {
    variant: 'secondary',
    size: 'l',
    children: 'Большая кнопка',
  },
};

export const Disabled: Story = {
  args: {
    variant: 'primary',
    disabled: true,
    children: 'Отключена',
  },
};

export const DisabledSecondary: Story = {
  args: {
    variant: 'secondary',
    disabled: true,
    children: 'Отключена',
  },
};

export const Loading: Story = {
  args: {
    variant: 'primary',
    loading: true,
    children: 'Загрузка...',
  },
};

export const Clear: Story = {
  args: {
    variant: 'clear',
    size: 'm',
  },
};

export const ClearLarge: Story = {
  args: {
    variant: 'clear',
    size: 'l',
    children: 'Большая кнопка',
  },
};

export const ClearDisabled: Story = {
  args: {
    variant: 'clear',
    disabled: true,
    children: 'Отключена',
  },
};

export const ClearLoading: Story = {
  args: {
    variant: 'clear',
    loading: true,
    children: 'Загрузка...',
  },
};

export const AllVariants: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'flex', flexDirection: 'row', gap: '1rem' }}>
        <p>Default</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Primary L
          </AppButton>

          <AppButton
            variant="primary"
            size="m"
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Primary M
          </AppButton>

          <AppButton
            variant="primary"
            size="s"
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Primary S
          </AppButton>

          <AppButton
            variant="primary"
            size="xs"
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Primary L
          </AppButton>

          <AppButton
            variant="primary"
            size="m"
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Primary M
          </AppButton>

          <AppButton
            variant="primary"
            size="s"
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Primary S
          </AppButton>

          <AppButton
            variant="primary"
            size="xs"
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Primary L
          </AppButton>

          <AppButton
            variant="primary"
            size="m"
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Primary M
          </AppButton>

          <AppButton
            variant="primary"
            size="s"
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Primary S
          </AppButton>

          <AppButton
            variant="primary"
            size="xs"
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
          >
            Primary L
          </AppButton>
          <AppButton
            variant="primary"
            size="m"
          >
            Primary M
          </AppButton>
          <AppButton
            variant="primary"
            size="s"
          >
            Primary S
          </AppButton>
          <AppButton
            variant="primary"
            size="xs"
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            onlyIcon
          >
            <DummyIcon
              width={24}
              height={24}
            />
          </AppButton>
          <AppButton
            variant="primary"
            size="m"
            onlyIcon
          >
            <DummyIcon
              width={20}
              height={20}
            />
          </AppButton>
          <AppButton
            variant="primary"
            size="s"
            onlyIcon
          >
            <DummyIcon
              width={16}
              height={16}
            />
          </AppButton>
          <AppButton
            variant="primary"
            size="xs"
            onlyIcon
          >
            <DummyIcon
              width={12}
              height={12}
            />
          </AppButton>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'row', gap: '1rem' }}>
        <p>
          Push
          <br />
          <br />
          Hover
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            data-active="true"
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Primary L
          </AppButton>

          <AppButton
            variant="primary"
            size="m"
            data-active="true"
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Primary M
          </AppButton>

          <AppButton
            variant="primary"
            size="s"
            data-active="true"
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Primary S
          </AppButton>

          <AppButton
            variant="primary"
            size="xs"
            data-active="true"
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            data-active="true"
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Primary L
          </AppButton>

          <AppButton
            variant="primary"
            size="m"
            data-active="true"
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Primary M
          </AppButton>

          <AppButton
            variant="primary"
            size="s"
            data-active="true"
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Primary S
          </AppButton>

          <AppButton
            variant="primary"
            size="xs"
            data-active="true"
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            data-active="true"
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Primary L
          </AppButton>

          <AppButton
            variant="primary"
            size="m"
            data-active="true"
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Primary M
          </AppButton>

          <AppButton
            variant="primary"
            size="s"
            data-active="true"
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Primary S
          </AppButton>

          <AppButton
            variant="primary"
            size="xs"
            data-active="true"
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            data-active="true"
          >
            Primary L
          </AppButton>
          <AppButton
            variant="primary"
            size="m"
            data-active="true"
          >
            Primary M
          </AppButton>
          <AppButton
            variant="primary"
            size="s"
            data-active="true"
          >
            Primary S
          </AppButton>
          <AppButton
            variant="primary"
            size="xs"
            data-active="true"
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            data-active="true"
            onlyIcon
          >
            <DummyIcon
              width={24}
              height={24}
            />
          </AppButton>
          <AppButton
            variant="primary"
            size="m"
            data-active="true"
            onlyIcon
          >
            <DummyIcon
              width={20}
              height={20}
            />
          </AppButton>
          <AppButton
            variant="primary"
            size="s"
            data-active="true"
            onlyIcon
          >
            <DummyIcon
              width={16}
              height={16}
            />
          </AppButton>
          <AppButton
            variant="primary"
            size="xs"
            data-active="true"
            onlyIcon
          >
            <DummyIcon
              width={12}
              height={12}
            />
          </AppButton>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'row', gap: '1rem' }}>
        <p>Disab</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            disabled
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Primary L
          </AppButton>

          <AppButton
            variant="primary"
            size="m"
            disabled
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Primary M
          </AppButton>

          <AppButton
            variant="primary"
            size="s"
            disabled
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Primary S
          </AppButton>

          <AppButton
            variant="primary"
            size="xs"
            disabled
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            disabled
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Primary L
          </AppButton>

          <AppButton
            variant="primary"
            size="m"
            disabled
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Primary M
          </AppButton>

          <AppButton
            variant="primary"
            size="s"
            disabled
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Primary S
          </AppButton>

          <AppButton
            variant="primary"
            size="xs"
            disabled
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            disabled
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Primary L
          </AppButton>

          <AppButton
            variant="primary"
            size="m"
            disabled
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Primary M
          </AppButton>

          <AppButton
            variant="primary"
            size="s"
            disabled
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Primary S
          </AppButton>

          <AppButton
            variant="primary"
            size="xs"
            disabled
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            disabled
          >
            Primary L
          </AppButton>
          <AppButton
            variant="primary"
            size="m"
            disabled
          >
            Primary M
          </AppButton>
          <AppButton
            variant="primary"
            size="s"
            disabled
          >
            Primary S
          </AppButton>
          <AppButton
            variant="primary"
            size="xs"
            disabled
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            disabled
            onlyIcon
          >
            <DummyIcon
              width={24}
              height={24}
            />
          </AppButton>
          <AppButton
            variant="primary"
            size="m"
            disabled
            onlyIcon
          >
            <DummyIcon
              width={20}
              height={20}
            />
          </AppButton>
          <AppButton
            variant="primary"
            size="s"
            disabled
            onlyIcon
          >
            <DummyIcon
              width={16}
              height={16}
            />
          </AppButton>
          <AppButton
            variant="primary"
            size="xs"
            disabled
            onlyIcon
          >
            <DummyIcon
              width={12}
              height={12}
            />
          </AppButton>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'row', gap: '1rem' }}>
        <p>Load</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            loading
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Primary L
          </AppButton>

          <AppButton
            variant="primary"
            size="m"
            loading
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Primary M
          </AppButton>

          <AppButton
            variant="primary"
            size="s"
            loading
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Primary S
          </AppButton>

          <AppButton
            variant="primary"
            size="xs"
            loading
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            loading
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Primary L
          </AppButton>

          <AppButton
            variant="primary"
            size="m"
            loading
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Primary M
          </AppButton>

          <AppButton
            variant="primary"
            size="s"
            loading
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Primary S
          </AppButton>

          <AppButton
            variant="primary"
            size="xs"
            loading
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            loading
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Primary L
          </AppButton>

          <AppButton
            variant="primary"
            size="m"
            loading
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Primary M
          </AppButton>

          <AppButton
            variant="primary"
            size="s"
            loading
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Primary S
          </AppButton>

          <AppButton
            variant="primary"
            size="xs"
            loading
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            loading
          >
            Primary L
          </AppButton>
          <AppButton
            variant="primary"
            size="m"
            loading
          >
            Primary M
          </AppButton>
          <AppButton
            variant="primary"
            size="s"
            loading
          >
            Primary S
          </AppButton>
          <AppButton
            variant="primary"
            size="xs"
            loading
          >
            Primary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="primary"
            size="l"
            loading
            onlyIcon
          >
            <DummyIcon
              width={24}
              height={24}
            />
          </AppButton>
          <AppButton
            variant="primary"
            size="m"
            loading
            onlyIcon
          >
            <DummyIcon
              width={20}
              height={20}
            />
          </AppButton>
          <AppButton
            variant="primary"
            size="s"
            loading
            onlyIcon
          >
            <DummyIcon
              width={16}
              height={16}
            />
          </AppButton>
          <AppButton
            variant="primary"
            size="xs"
            loading
            onlyIcon
          >
            <DummyIcon
              width={12}
              height={12}
            />
          </AppButton>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>Secondary ↓</div>

      <div style={{ display: 'flex', flexDirection: 'row', gap: '1rem' }}>
        <p>Default</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Secondary L
          </AppButton>

          <AppButton
            variant="secondary"
            size="m"
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Secondary M
          </AppButton>

          <AppButton
            variant="secondary"
            size="s"
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Secondary S
          </AppButton>

          <AppButton
            variant="secondary"
            size="xs"
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Secondary L
          </AppButton>

          <AppButton
            variant="secondary"
            size="m"
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Secondary M
          </AppButton>

          <AppButton
            variant="secondary"
            size="s"
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Secondary S
          </AppButton>

          <AppButton
            variant="secondary"
            size="xs"
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Secondary L
          </AppButton>

          <AppButton
            variant="secondary"
            size="m"
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Secondary M
          </AppButton>

          <AppButton
            variant="secondary"
            size="s"
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Secondary S
          </AppButton>

          <AppButton
            variant="secondary"
            size="xs"
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
          >
            Secondary L
          </AppButton>
          <AppButton
            variant="secondary"
            size="m"
          >
            Secondary M
          </AppButton>
          <AppButton
            variant="secondary"
            size="s"
          >
            Secondary S
          </AppButton>
          <AppButton
            variant="secondary"
            size="xs"
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            onlyIcon
          >
            <DummyIcon
              width={24}
              height={24}
            />
          </AppButton>
          <AppButton
            variant="secondary"
            size="m"
            onlyIcon
          >
            <DummyIcon
              width={20}
              height={20}
            />
          </AppButton>
          <AppButton
            variant="secondary"
            size="s"
            onlyIcon
          >
            <DummyIcon
              width={16}
              height={16}
            />
          </AppButton>
          <AppButton
            variant="secondary"
            size="xs"
            onlyIcon
          >
            <DummyIcon
              width={12}
              height={12}
            />
          </AppButton>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'row', gap: '1rem' }}>
        <p>
          Push
          <br />
          <br />
          Hover
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            data-active="true"
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Secondary L
          </AppButton>

          <AppButton
            variant="secondary"
            size="m"
            data-active="true"
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Secondary M
          </AppButton>

          <AppButton
            variant="secondary"
            size="s"
            data-active="true"
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Secondary S
          </AppButton>

          <AppButton
            variant="secondary"
            size="xs"
            data-active="true"
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            data-active="true"
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Secondary L
          </AppButton>

          <AppButton
            variant="secondary"
            size="m"
            data-active="true"
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Secondary M
          </AppButton>

          <AppButton
            variant="secondary"
            size="s"
            data-active="true"
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Secondary S
          </AppButton>

          <AppButton
            variant="secondary"
            size="xs"
            data-active="true"
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            data-active="true"
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Secondary L
          </AppButton>

          <AppButton
            variant="secondary"
            size="m"
            data-active="true"
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Secondary M
          </AppButton>

          <AppButton
            variant="secondary"
            size="s"
            data-active="true"
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Secondary S
          </AppButton>

          <AppButton
            variant="secondary"
            size="xs"
            data-active="true"
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            data-active="true"
          >
            Secondary L
          </AppButton>
          <AppButton
            variant="secondary"
            size="m"
            data-active="true"
          >
            Secondary M
          </AppButton>
          <AppButton
            variant="secondary"
            size="s"
            data-active="true"
          >
            Secondary S
          </AppButton>
          <AppButton
            variant="secondary"
            size="xs"
            data-active="true"
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            data-active="true"
            onlyIcon
          >
            <DummyIcon
              width={24}
              height={24}
            />
          </AppButton>
          <AppButton
            variant="secondary"
            size="m"
            data-active="true"
            onlyIcon
          >
            <DummyIcon
              width={20}
              height={20}
            />
          </AppButton>
          <AppButton
            variant="secondary"
            size="s"
            data-active="true"
            onlyIcon
          >
            <DummyIcon
              width={16}
              height={16}
            />
          </AppButton>
          <AppButton
            variant="secondary"
            size="xs"
            data-active="true"
            onlyIcon
          >
            <DummyIcon
              width={12}
              height={12}
            />
          </AppButton>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'row', gap: '1rem' }}>
        <p>Disab</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            disabled
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Secondary L
          </AppButton>

          <AppButton
            variant="secondary"
            size="m"
            disabled
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Secondary M
          </AppButton>

          <AppButton
            variant="secondary"
            size="s"
            disabled
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Secondary S
          </AppButton>

          <AppButton
            variant="secondary"
            size="xs"
            disabled
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            disabled
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Secondary L
          </AppButton>

          <AppButton
            variant="secondary"
            size="m"
            disabled
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Secondary M
          </AppButton>

          <AppButton
            variant="secondary"
            size="s"
            disabled
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Secondary S
          </AppButton>

          <AppButton
            variant="secondary"
            size="xs"
            disabled
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            disabled
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Secondary L
          </AppButton>

          <AppButton
            variant="secondary"
            size="m"
            disabled
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Secondary M
          </AppButton>

          <AppButton
            variant="secondary"
            size="s"
            disabled
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Secondary S
          </AppButton>

          <AppButton
            variant="secondary"
            size="xs"
            disabled
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            disabled
          >
            Secondary L
          </AppButton>
          <AppButton
            variant="secondary"
            size="m"
            disabled
          >
            Secondary M
          </AppButton>
          <AppButton
            variant="secondary"
            size="s"
            disabled
          >
            Secondary S
          </AppButton>
          <AppButton
            variant="secondary"
            size="xs"
            disabled
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            disabled
            onlyIcon
          >
            <DummyIcon
              width={24}
              height={24}
            />
          </AppButton>
          <AppButton
            variant="secondary"
            size="m"
            disabled
            onlyIcon
          >
            <DummyIcon
              width={20}
              height={20}
            />
          </AppButton>
          <AppButton
            variant="secondary"
            size="s"
            disabled
            onlyIcon
          >
            <DummyIcon
              width={16}
              height={16}
            />
          </AppButton>
          <AppButton
            variant="secondary"
            size="xs"
            disabled
            onlyIcon
          >
            <DummyIcon
              width={12}
              height={12}
            />
          </AppButton>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'row', gap: '1rem' }}>
        <p>Load</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            loading
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Secondary L
          </AppButton>

          <AppButton
            variant="secondary"
            size="m"
            loading
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Secondary M
          </AppButton>

          <AppButton
            variant="secondary"
            size="s"
            loading
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Secondary S
          </AppButton>

          <AppButton
            variant="secondary"
            size="xs"
            loading
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            loading
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Secondary L
          </AppButton>

          <AppButton
            variant="secondary"
            size="m"
            loading
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Secondary M
          </AppButton>

          <AppButton
            variant="secondary"
            size="s"
            loading
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Secondary S
          </AppButton>

          <AppButton
            variant="secondary"
            size="xs"
            loading
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            loading
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Secondary L
          </AppButton>

          <AppButton
            variant="secondary"
            size="m"
            loading
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Secondary M
          </AppButton>

          <AppButton
            variant="secondary"
            size="s"
            loading
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Secondary S
          </AppButton>

          <AppButton
            variant="secondary"
            size="xs"
            loading
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            loading
          >
            Secondary L
          </AppButton>
          <AppButton
            variant="secondary"
            size="m"
            loading
          >
            Secondary M
          </AppButton>
          <AppButton
            variant="secondary"
            size="s"
            loading
          >
            Secondary S
          </AppButton>
          <AppButton
            variant="secondary"
            size="xs"
            loading
          >
            Secondary XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="secondary"
            size="l"
            loading
            onlyIcon
          >
            <DummyIcon
              width={24}
              height={24}
            />
          </AppButton>
          <AppButton
            variant="secondary"
            size="m"
            loading
            onlyIcon
          >
            <DummyIcon
              width={20}
              height={20}
            />
          </AppButton>
          <AppButton
            variant="secondary"
            size="s"
            loading
            onlyIcon
          >
            <DummyIcon
              width={16}
              height={16}
            />
          </AppButton>
          <AppButton
            variant="secondary"
            size="xs"
            loading
            onlyIcon
          >
            <DummyIcon
              width={12}
              height={12}
            />
          </AppButton>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>Clear ↓</div>

      <div style={{ display: 'flex', flexDirection: 'row', gap: '1rem' }}>
        <p>Default</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Clear L
          </AppButton>

          <AppButton
            variant="clear"
            size="m"
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Clear M
          </AppButton>

          <AppButton
            variant="clear"
            size="s"
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Clear S
          </AppButton>

          <AppButton
            variant="clear"
            size="xs"
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Clear L
          </AppButton>

          <AppButton
            variant="clear"
            size="m"
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Clear M
          </AppButton>

          <AppButton
            variant="clear"
            size="s"
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Clear S
          </AppButton>

          <AppButton
            variant="clear"
            size="xs"
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Clear L
          </AppButton>

          <AppButton
            variant="clear"
            size="m"
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Clear M
          </AppButton>

          <AppButton
            variant="clear"
            size="s"
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Clear S
          </AppButton>

          <AppButton
            variant="clear"
            size="xs"
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
          >
            Clear L
          </AppButton>
          <AppButton
            variant="clear"
            size="m"
          >
            Clear M
          </AppButton>
          <AppButton
            variant="clear"
            size="s"
          >
            Clear S
          </AppButton>
          <AppButton
            variant="clear"
            size="xs"
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            onlyIcon
          >
            <DummyIcon
              width={24}
              height={24}
            />
          </AppButton>
          <AppButton
            variant="clear"
            size="m"
            onlyIcon
          >
            <DummyIcon
              width={20}
              height={20}
            />
          </AppButton>
          <AppButton
            variant="clear"
            size="s"
            onlyIcon
          >
            <DummyIcon
              width={16}
              height={16}
            />
          </AppButton>
          <AppButton
            variant="clear"
            size="xs"
            onlyIcon
          >
            <DummyIcon
              width={12}
              height={12}
            />
          </AppButton>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'row', gap: '1rem' }}>
        <p>
          Push
          <br />
          <br />
          Hover
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            data-active="true"
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Clear L
          </AppButton>

          <AppButton
            variant="clear"
            size="m"
            data-active="true"
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Clear M
          </AppButton>

          <AppButton
            variant="clear"
            size="s"
            data-active="true"
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Clear S
          </AppButton>

          <AppButton
            variant="clear"
            size="xs"
            data-active="true"
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            data-active="true"
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Clear L
          </AppButton>

          <AppButton
            variant="clear"
            size="m"
            data-active="true"
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Clear M
          </AppButton>

          <AppButton
            variant="clear"
            size="s"
            data-active="true"
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Clear S
          </AppButton>

          <AppButton
            variant="clear"
            size="xs"
            data-active="true"
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            data-active="true"
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Clear L
          </AppButton>

          <AppButton
            variant="clear"
            size="m"
            data-active="true"
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Clear M
          </AppButton>

          <AppButton
            variant="clear"
            size="s"
            data-active="true"
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Clear S
          </AppButton>

          <AppButton
            variant="clear"
            size="xs"
            data-active="true"
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            data-active="true"
          >
            Clear L
          </AppButton>
          <AppButton
            variant="clear"
            size="m"
            data-active="true"
          >
            Clear M
          </AppButton>
          <AppButton
            variant="clear"
            size="s"
            data-active="true"
          >
            Clear S
          </AppButton>
          <AppButton
            variant="clear"
            size="xs"
            data-active="true"
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            data-active="true"
            onlyIcon
          >
            <DummyIcon
              width={24}
              height={24}
            />
          </AppButton>
          <AppButton
            variant="clear"
            size="m"
            data-active="true"
            onlyIcon
          >
            <DummyIcon
              width={20}
              height={20}
            />
          </AppButton>
          <AppButton
            variant="clear"
            size="s"
            data-active="true"
            onlyIcon
          >
            <DummyIcon
              width={16}
              height={16}
            />
          </AppButton>
          <AppButton
            variant="clear"
            size="xs"
            data-active="true"
            onlyIcon
          >
            <DummyIcon
              width={12}
              height={12}
            />
          </AppButton>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'row', gap: '1rem' }}>
        <p>Disabled</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            disabled
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Clear L
          </AppButton>

          <AppButton
            variant="clear"
            size="m"
            disabled
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Clear M
          </AppButton>

          <AppButton
            variant="clear"
            size="s"
            disabled
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Clear S
          </AppButton>

          <AppButton
            variant="clear"
            size="xs"
            disabled
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            disabled
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Clear L
          </AppButton>

          <AppButton
            variant="clear"
            size="m"
            disabled
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Clear M
          </AppButton>

          <AppButton
            variant="clear"
            size="s"
            disabled
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Clear S
          </AppButton>

          <AppButton
            variant="clear"
            size="xs"
            disabled
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            disabled
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Clear L
          </AppButton>

          <AppButton
            variant="clear"
            size="m"
            disabled
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Clear M
          </AppButton>

          <AppButton
            variant="clear"
            size="s"
            disabled
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Clear S
          </AppButton>

          <AppButton
            variant="clear"
            size="xs"
            disabled
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            disabled
          >
            Clear L
          </AppButton>
          <AppButton
            variant="clear"
            size="m"
            disabled
          >
            Clear M
          </AppButton>
          <AppButton
            variant="clear"
            size="s"
            disabled
          >
            Clear S
          </AppButton>
          <AppButton
            variant="clear"
            size="xs"
            disabled
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            disabled
            onlyIcon
          >
            <DummyIcon
              width={24}
              height={24}
            />
          </AppButton>
          <AppButton
            variant="clear"
            size="m"
            disabled
            onlyIcon
          >
            <DummyIcon
              width={20}
              height={20}
            />
          </AppButton>
          <AppButton
            variant="clear"
            size="s"
            disabled
            onlyIcon
          >
            <DummyIcon
              width={16}
              height={16}
            />
          </AppButton>
          <AppButton
            variant="clear"
            size="xs"
            disabled
            onlyIcon
          >
            <DummyIcon
              width={12}
              height={12}
            />
          </AppButton>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'row', gap: '1rem' }}>
        <p>Loading</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            loading
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Clear L
          </AppButton>

          <AppButton
            variant="clear"
            size="m"
            loading
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Clear M
          </AppButton>

          <AppButton
            variant="clear"
            size="s"
            loading
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Clear S
          </AppButton>

          <AppButton
            variant="clear"
            size="xs"
            loading
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            loading
            rightSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Clear L
          </AppButton>

          <AppButton
            variant="clear"
            size="m"
            loading
            rightSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Clear M
          </AppButton>

          <AppButton
            variant="clear"
            size="s"
            loading
            rightSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Clear S
          </AppButton>

          <AppButton
            variant="clear"
            size="xs"
            loading
            rightSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            loading
            leftSection={
              <DummyIcon
                width={24}
                height={24}
              />
            }
          >
            Clear L
          </AppButton>

          <AppButton
            variant="clear"
            size="m"
            loading
            leftSection={
              <DummyIcon
                width={20}
                height={20}
              />
            }
          >
            Clear M
          </AppButton>

          <AppButton
            variant="clear"
            size="s"
            loading
            leftSection={
              <DummyIcon
                width={16}
                height={16}
              />
            }
          >
            Clear S
          </AppButton>

          <AppButton
            variant="clear"
            size="xs"
            loading
            leftSection={
              <DummyIcon
                width={12}
                height={12}
              />
            }
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            loading
          >
            Clear L
          </AppButton>
          <AppButton
            variant="clear"
            size="m"
            loading
          >
            Clear M
          </AppButton>
          <AppButton
            variant="clear"
            size="s"
            loading
          >
            Clear S
          </AppButton>
          <AppButton
            variant="clear"
            size="xs"
            loading
          >
            Clear XS
          </AppButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <AppButton
            variant="clear"
            size="l"
            loading
            onlyIcon
          >
            <DummyIcon
              width={24}
              height={24}
            />
          </AppButton>
          <AppButton
            variant="clear"
            size="m"
            loading
            onlyIcon
          >
            <DummyIcon
              width={20}
              height={20}
            />
          </AppButton>
          <AppButton
            variant="clear"
            size="s"
            loading
            onlyIcon
          >
            <DummyIcon
              width={16}
              height={16}
            />
          </AppButton>
          <AppButton
            variant="clear"
            size="xs"
            loading
            onlyIcon
          >
            <DummyIcon
              width={12}
              height={12}
            />
          </AppButton>
        </div>
      </div>
    </div>
  ),
};
