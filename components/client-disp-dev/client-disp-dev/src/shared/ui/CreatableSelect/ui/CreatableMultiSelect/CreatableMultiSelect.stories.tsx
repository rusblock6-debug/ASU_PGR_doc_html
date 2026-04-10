import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';

import { ConfirmProvider, useConfirm } from '@/shared/lib/confirm';
import type { SelectOption } from '@/shared/ui/types';

import { CreatableMultiSelect } from './CreatableMultiSelect';

interface Tag extends SelectOption {
  color?: string;
}

const initialOptions: Tag[] = [
  { value: '1', label: 'Frontend', color: '#3b82f6' },
  { value: '2', label: 'Backend', color: '#22c55e' },
  { value: '3', label: 'DevOps', color: '#f59e0b' },
  { value: '4', label: 'Design', color: '#ec4899' },
  { value: '5', label: 'QA', color: '#8b5cf6' },
  { value: '6', label: 'Mobile', color: '#06b6d4' },
  { value: '7', label: 'Data Science', color: '#ef4444' },
];

const meta: Meta<typeof CreatableMultiSelect> = {
  title: 'Shared/CreatableMultiSelect',
  component: CreatableMultiSelect,
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
          'Мульти-селект с возможностью создания, редактирования и удаления опций. Выбранные значения отображаются как pills с возможностью удаления.',
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof CreatableMultiSelect>;

/** Базовый пример без возможности редактирования/удаления */
export const Basic: Story = {
  render: () => {
    const [values, setValues] = useState<string[]>([]);

    return (
      <CreatableMultiSelect
        options={initialOptions}
        value={values}
        onChange={(options) => setValues(options.map((o) => o.value))}
        label="Теги"
        placeholder="Выберите теги"
      />
    );
  },
};

/** Полный пример с созданием, редактированием и удалением */
export const FullCRUD: Story = {
  render: function FullCRUDStory() {
    const confirm = useConfirm();
    const [options, setOptions] = useState<Tag[]>(initialOptions);
    const [values, setValues] = useState<string[]>([]);
    const [logs, setLogs] = useState<string[]>([]);

    const addLog = (message: string) => {
      setLogs((prev) => [...prev.slice(-9), `${new Date().toLocaleTimeString()}: ${message}`]);
    };

    const handleChange = (selectedOptions: readonly Tag[]) => {
      setValues(selectedOptions.map((o) => o.value));
      addLog(`📝 Выбрано: [${selectedOptions.map((o) => o.label).join(', ')}]`);
    };

    const handleCreate = async (label: string) => {
      addLog(`⏳ Создание тега: "${label}"...`);

      // Эмуляция задержки API
      await new Promise((resolve) => setTimeout(resolve, 300));

      const newOption: Tag = {
        value: `new-${Date.now()}`,
        label,
      };
      setOptions((prev) => [...prev, newOption]);
      setValues((prev) => [...prev, newOption.value]);
      addLog(`✅ Создан новый тег: "${label}"`);
    };

    const handleRename = async (optionValue: string, newLabel: string): Promise<Tag> => {
      // Эмуляция задержки API
      await new Promise((resolve) => setTimeout(resolve, 300));

      const updated = options.find((o) => o.value === optionValue);
      if (!updated) throw new Error('Опция не найдена');

      const oldLabel = updated.label;
      setOptions((prev) => prev.map((o) => (o.value === optionValue ? { ...o, label: newLabel } : o)));

      addLog(`✏️ Переименовано: "${oldLabel}" → "${newLabel}"`);
      return { ...updated, label: newLabel };
    };

    const handleDelete = async (option: Tag) => {
      const isConfirmed = await confirm({
        title: 'Удаление',
        message: `Вы уверены, что хотите удалить тег: «${option.label}»?`,
        confirmText: 'Удалить',
        cancelText: 'Отмена',
      });

      if (!isConfirmed) return false;

      // Эмуляция задержки API
      await new Promise((resolve) => setTimeout(resolve, 300));

      setOptions((prev) => prev.filter((o) => o.value !== option.value));
      setValues((prev) => prev.filter((v) => v !== option.value));

      addLog(`🗑️ Удалён тег: "${option.label}"`);

      return true;
    };

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <CreatableMultiSelect
          options={options}
          value={values}
          onChange={handleChange}
          onCreate={handleCreate}
          onRename={handleRename}
          onDelete={handleDelete}
          label="Теги проекта"
          placeholder="Выберите или создайте теги"
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
            <li>Выберите несколько тегов из списка</li>
            <li>Введите текст и выберите «Создать» для добавления нового тега</li>
            <li>Нажмите × на pill для удаления из выбранных</li>
            <li>Нажмите ⋮ на опции для редактирования или удаления тега</li>
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
          Всего тегов: {options.length} | Выбрано: {values.length}
        </div>
      </div>
    );
  },
};

/** Пример с предустановленными значениями */
export const WithPreselectedValues: Story = {
  render: () => {
    const [values, setValues] = useState<string[]>(['1', '2', '3']);

    return (
      <CreatableMultiSelect
        options={initialOptions}
        value={values}
        onChange={(options) => setValues(options.map((o) => o.value))}
        label="Теги"
        placeholder="Выберите теги"
      />
    );
  },
};

/** Пример с ограничением количества */
export const WithMaxValues: Story = {
  render: () => {
    const [values, setValues] = useState<string[]>(['1']);

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <CreatableMultiSelect
          options={initialOptions}
          value={values}
          onChange={(options) => setValues(options.map((o) => o.value))}
          maxValues={3}
          label="Теги (максимум 3)"
          placeholder="Выберите до 3 тегов"
        />
        <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.5)' }}>Выбрано: {values.length} / 3</div>
      </div>
    );
  },
};

/** Скрывать выбранные опции из списка */
export const HidePickedOptions: Story = {
  render: () => {
    const [values, setValues] = useState<string[]>(['1', '2']);

    return (
      <CreatableMultiSelect
        options={initialOptions}
        value={values}
        onChange={(options) => setValues(options.map((o) => o.value))}
        hidePickedOptions
        label="Теги"
        placeholder="Выбранные теги скрыты из списка"
      />
    );
  },
};

/** Состояние ошибки */
export const WithError: Story = {
  render: () => {
    const [values, setValues] = useState<string[]>([]);

    return (
      <CreatableMultiSelect
        options={initialOptions}
        value={values}
        onChange={(options) => setValues(options.map((o) => o.value))}
        label="Теги"
        placeholder="Выберите теги"
        withAsterisk={true}
        error="Выберите хотя бы один тег"
      />
    );
  },
};

/** Только для чтения */
export const ReadOnly: Story = {
  render: () => (
    <CreatableMultiSelect
      options={initialOptions}
      value={['1', '3', '5']}
      label="Теги"
      readOnly
    />
  ),
};

/** Отключённое состояние */
export const Disabled: Story = {
  render: () => (
    <CreatableMultiSelect
      options={initialOptions}
      value={['1', '2']}
      label="Теги"
      disabled
    />
  ),
};

/** Пустой список опций */
export const EmptyOptions: Story = {
  render: () => {
    const [options, setOptions] = useState<Tag[]>([]);
    const [values, setValues] = useState<string[]>([]);

    const handleCreate = (label: string) => {
      const newOption: Tag = {
        value: `new-${Date.now()}`,
        label,
      };
      setOptions((prev) => [...prev, newOption]);
      setValues((prev) => [...prev, newOption.value]);
    };

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <CreatableMultiSelect
          options={options}
          value={values}
          onChange={(opts) => setValues(opts.map((o) => o.value))}
          onCreate={handleCreate}
          label="Теги"
          placeholder="Начните вводить для создания"
        />
        <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.5)' }}>Создано тегов: {options.length}</div>
      </div>
    );
  },
};

/** Много выбранных значений */
export const ManySelectedValues: Story = {
  render: () => {
    const [values, setValues] = useState<string[]>(['1', '2', '3', '4', '5', '6']);

    return (
      <CreatableMultiSelect
        options={initialOptions}
        value={values}
        onChange={(options) => setValues(options.map((o) => o.value))}
        label="Теги"
        placeholder="Выберите теги"
      />
    );
  },
};
