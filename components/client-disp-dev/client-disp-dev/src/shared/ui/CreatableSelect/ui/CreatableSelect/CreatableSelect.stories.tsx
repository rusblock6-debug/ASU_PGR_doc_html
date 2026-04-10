import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';

import { ConfirmProvider, useConfirm } from '@/shared/lib/confirm';
import type { SelectOption } from '@/shared/ui/types';

import { CreatableSelect } from '../../index';

interface CarModel extends SelectOption {
  year?: number;
}

const initialOptions: CarModel[] = [
  { value: '1', label: 'Toyota Camry', year: 2023 },
  { value: '2', label: 'Honda Accord', year: 2022 },
  { value: '3', label: 'BMW X5', year: 2024 },
  { value: '4', label: 'Mercedes-Benz E-Class', year: 2023 },
  { value: '5', label: 'Audi A6', year: 2022 },
];

const meta: Meta<typeof CreatableSelect> = {
  title: 'Shared/CreatableSelect',
  component: CreatableSelect,
  tags: ['autodocs'],
  decorators: [
    // eslint-disable-next-line @typescript-eslint/naming-convention
    (Story) => (
      <ConfirmProvider>
        <div style={{ maxWidth: 620, minHeight: 700 }}>
          <Story />
        </div>
      </ConfirmProvider>
    ),
  ],
  parameters: {
    docs: {
      description: {
        component:
          'Комбобокс с возможностью создания, редактирования и удаления опций. Поддерживает поиск по существующим опциям и создание новых значений.',
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof CreatableSelect>;

/** Базовый пример без возможности редактирования/удаления */
export const Basic: Story = {
  render: () => {
    const [value, setValue] = useState<string | null>(null);

    return (
      <CreatableSelect
        options={initialOptions}
        value={value}
        onChange={(option) => setValue(option.value)}
        label="Модель автомобиля"
        placeholder="Выберите или введите модель"
      />
    );
  },
};

/** Полный пример с созданием, редактированием и удалением */
export const FullCRUD: Story = {
  render: function FullCRUDStory() {
    const confirm = useConfirm();
    const [options, setOptions] = useState<CarModel[]>(initialOptions);
    const [value, setValue] = useState<string | null>(null);
    const [logs, setLogs] = useState<string[]>([]);

    const addLog = (message: string) => {
      setLogs((prev) => [...prev.slice(-9), `${new Date().toLocaleTimeString()}: ${message}`]);
    };

    const handleChange = (option: CarModel) => {
      setValue(option.value);
      addLog(`📝 Выбрана модель: "${option.label}" (${option.year} г.)`);
    };

    const handleCreate = async (label: string) => {
      addLog(`⏳ Создание модели: "${label}"...`);

      // Эмуляция задержки API
      await new Promise((resolve) => setTimeout(resolve, 300));

      const newOption: CarModel = {
        value: `new-${Date.now()}`,
        label,
        year: new Date().getFullYear(),
      };
      setOptions((prev) => [...prev, newOption]);
      setValue(newOption.value);
      addLog(`✅ Создана новая модель: "${label}"`);
    };

    const handleRename = async (optionValue: string, newLabel: string): Promise<CarModel> => {
      // Эмуляция задержки API
      await new Promise((resolve) => setTimeout(resolve, 300));

      const updated = options.find((o) => o.value === optionValue);
      if (!updated) throw new Error('Опция не найдена');

      const oldLabel = updated.label;
      setOptions((prev) => prev.map((o) => (o.value === optionValue ? { ...o, label: newLabel } : o)));

      addLog(`✏️ Переименовано: "${oldLabel}" → "${newLabel}"`);
      return { ...updated, label: newLabel };
    };

    const handleDelete = async (option: CarModel) => {
      // Родитель показывает подтверждение
      const isConfirmed = await confirm({
        title: 'Удаление',
        message: `Вы уверены, что хотите удалить модель: «${option.label}»?`,
        confirmText: 'Удалить',
        cancelText: 'Отмена',
      });

      if (!isConfirmed) return false;

      // Эмуляция задержки API
      await new Promise((resolve) => setTimeout(resolve, 300));

      setOptions((prev) => prev.filter((o) => o.value !== option.value));

      if (value === option.value) {
        setValue(null);
      }

      addLog(`🗑️ Удалена модель: "${option.label}"`);

      return true;
    };

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <CreatableSelect
          options={options}
          value={value}
          onChange={handleChange}
          onCreate={handleCreate}
          onRename={handleRename}
          onDelete={handleDelete}
          label="Модель автомобиля"
          placeholder="Выберите, введите или создайте модель"
          withAsterisk={true}
        />

        <div
          style={{
            padding: '0.75rem',
            background: 'rgba(255, 255, 255, 0.05)',
            borderRadius: '8px',
            fontSize: '12px',
          }}
        >
          <div style={{ marginBottom: '0.5rem', color: 'rgba(255, 255, 255, 0.6)' }}>
            <strong>Инструкция:</strong>
          </div>
          <ul style={{ margin: 0, paddingLeft: '1rem', color: 'rgba(255, 255, 255, 0.5)' }}>
            <li>Введите текст и выберите «Создать» для добавления новой модели</li>
            <li>Нажмите ⋮ на опции для редактирования или удаления</li>
            <li>В режиме редактирования измените название и нажмите Enter</li>
          </ul>
        </div>

        <div
          style={{
            padding: '0.75rem',
            background: 'rgba(0, 0, 0, 0.3)',
            borderRadius: '8px',
            fontSize: '11px',
            fontFamily: 'monospace',
            maxHeight: '150px',
            overflowY: 'auto',
          }}
        >
          <div style={{ marginBottom: '0.5rem', color: 'rgba(255, 255, 255, 0.4)' }}>Лог событий:</div>
          {logs.length === 0 ? (
            <div style={{ color: 'rgba(255, 255, 255, 0.3)' }}>Пока нет событий...</div>
          ) : (
            logs.map((log, i) => (
              <div
                key={i}
                style={{ color: 'rgba(255, 255, 255, 0.7)', marginBottom: '2px' }}
              >
                {log}
              </div>
            ))
          )}
        </div>

        <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.4)' }}>
          Текущих опций: {options.length} | Выбрано: {value ? options.find((o) => o.value === value)?.label : '—'}
        </div>
      </div>
    );
  },
};

/** Пример с предустановленным значением */
export const WithPreselectedValue: Story = {
  render: () => {
    const [value, setValue] = useState<string | null>('2');

    return (
      <CreatableSelect
        options={initialOptions}
        value={value}
        onChange={(option) => setValue(option.value)}
        label="Модель автомобиля"
        placeholder="Выберите модель"
      />
    );
  },
};

/** Состояние ошибки */
export const WithError: Story = {
  render: () => {
    const [value, setValue] = useState<string | null>(null);

    return (
      <CreatableSelect
        options={initialOptions}
        value={value}
        onChange={(option) => setValue(option.value)}
        label="Модель автомобиля"
        placeholder="Выберите модель"
        withAsterisk={true}
        error="Обязательное поле"
      />
    );
  },
};

/** Только для чтения */
export const ReadOnly: Story = {
  render: () => (
    <CreatableSelect
      options={initialOptions}
      value="3"
      label="Модель автомобиля"
      readOnly
    />
  ),
};

/** Отключённое состояние */
export const Disabled: Story = {
  render: () => (
    <CreatableSelect
      options={initialOptions}
      value="1"
      label="Модель автомобиля"
      disabled
    />
  ),
};

/** Пустой список опций */
export const EmptyOptions: Story = {
  render: () => {
    const [options, setOptions] = useState<CarModel[]>([]);
    const [value, setValue] = useState<string | null>(null);

    const handleCreate = (label: string) => {
      const newOption: CarModel = {
        value: `new-${Date.now()}`,
        label,
      };
      setOptions((prev) => [...prev, newOption]);
      setValue(newOption.value);
    };

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <CreatableSelect
          options={options}
          value={value}
          onChange={(option) => setValue(option.value)}
          onCreate={handleCreate}
          label="Модель автомобиля"
          placeholder="Начните вводить для создания"
        />
        <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.5)' }}>Создано моделей: {options.length}</div>
      </div>
    );
  },
};
