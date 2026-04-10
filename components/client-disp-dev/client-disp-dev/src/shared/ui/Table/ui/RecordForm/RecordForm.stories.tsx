import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, userEvent, within } from 'storybook/test';

import type { SelectOption } from '@/shared/ui/types';

import { ColumnDataTypes, type ColumnDef } from '../../types';

import { RecordForm } from './RecordForm';

interface DemoRecord {
  id: number;
  name: string;
  description: string;
  quantity: number;
  status: string;
  category: string;
  tags: { id: number }[];
  createdAt: string;
  scheduledDate: string;
  workTime: string;
  coordinates: { lat: number; lon: number };
  color: string;
  modelId: number;
  modelName: string;
}

const statusOptions: SelectOption[] = [
  { value: '1', label: 'Активен' },
  { value: '2', label: 'На паузе' },
  { value: '3', label: 'Завершён' },
  { value: '4', label: 'Отменён' },
];

const tagOptions: SelectOption[] = [
  { value: '1', label: 'Срочно' },
  { value: '2', label: 'Важно' },
  { value: '3', label: 'На проверку' },
  { value: '4', label: 'Архив' },
];

const modelOptions: (SelectOption & { capacity: number })[] = [
  { value: '1', label: 'БелАЗ-7513', capacity: 130 },
  { value: '2', label: 'Caterpillar 797F', capacity: 400 },
  { value: '3', label: 'Komatsu 930E', capacity: 320 },
];

const mockHandlers = {
  onCreate: async (label: string) => {
    await new Promise((r) => setTimeout(r, 500));
    const newOption = { value: String(Date.now()), label };
    // eslint-disable-next-line no-console
    console.log('Created:', newOption);
    return newOption;
  },
  onEdit: async (value: string, newLabel: string) => {
    await new Promise((r) => setTimeout(r, 300));
    // eslint-disable-next-line no-console
    console.log('Edited:', { value, newLabel });
    return { value, label: newLabel };
  },
  onDelete: async (value: string): Promise<boolean> => {
    await new Promise((r) => setTimeout(r, 300));
    // eslint-disable-next-line no-console
    console.log('Deleted:', value);
    return true;
  },
};

const columns: ColumnDef<DemoRecord>[] = [
  {
    accessorKey: 'id',
    header: 'ID',
    meta: {
      dataType: ColumnDataTypes.NUMBER,
      readOnly: true,
      required: false,
    },
  },
  {
    accessorKey: 'name',
    header: 'Название',
    meta: {
      required: false,
      dataType: ColumnDataTypes.TEXT,
    },
  },
  {
    accessorKey: 'quantity',
    header: 'Количество',
    meta: {
      dataType: ColumnDataTypes.NUMBER,
    },
  },
  {
    accessorKey: 'status',
    header: 'Статус',
    meta: {
      dataType: ColumnDataTypes.SELECT,
      options: statusOptions,
      valueType: 'string',
    },
  },
  {
    accessorKey: 'modelId',
    header: 'Модель техники (Reference)',
    meta: {
      dataType: ColumnDataTypes.EDITABLE_SELECT,
      options: modelOptions,
      valueType: 'string',
      autoFill: Object.fromEntries(
        modelOptions.map((model) => [
          String(model.value),
          {
            modelName: model.label,
          },
        ]),
      ),
      handlers: {
        ...mockHandlers,
        onCreate: async (label: string) => {
          await new Promise((r) => setTimeout(r, 500));
          const newOption = { value: String(Date.now()), label, capacity: 0 };
          // eslint-disable-next-line no-console
          console.log('Created model:', newOption);
          return newOption;
        },
      },
    },
  },
  {
    accessorKey: 'tags',
    header: 'Теги (мультивыбор)',
    meta: {
      dataType: ColumnDataTypes.MULTI_SELECT,
      options: tagOptions,
      handlers: mockHandlers,
    },
  },
  {
    accessorKey: 'createdAt',
    header: 'Дата создания (DateTimePicker)',
    meta: {
      dataType: ColumnDataTypes.DATETIME,
      columnWithMaxValue: 'scheduledDate',
    },
  },
  {
    accessorKey: 'scheduledDate',
    header: 'Дата по плану',
    meta: {
      dataType: ColumnDataTypes.DATE,
      columnWithMinValue: 'createdAt',
    },
  },
  {
    accessorKey: 'workTime',
    header: 'Время работы',
    meta: {
      dataType: ColumnDataTypes.TIME,
    },
  },
  {
    accessorKey: 'coordinates',
    header: 'Координаты',
    meta: {
      required: false,
      dataType: ColumnDataTypes.COORDINATES,
    },
  },
  {
    accessorKey: 'color',
    header: 'Цвет',
    meta: {
      dataType: ColumnDataTypes.COLOR,
    },
  },
  {
    accessorKey: 'modelName',
    header: 'Название модели',
    meta: {
      dataType: ColumnDataTypes.TEXT,
    },
  },
];

const initialData: Partial<DemoRecord> = {
  id: 42,
  name: 'Тестовая запись',
  quantity: 15,
  status: '1',
  category: '2',
  tags: [{ id: 1 }, { id: 3 }],
  createdAt: new Date().toISOString(),
  scheduledDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
  workTime: '08:30',
  coordinates: { lat: 55.7558, lon: 37.6173 },
  color: '#3B82F6',
  modelId: 2,
  modelName: 'Caterpillar 797F',
};

const meta: Meta<typeof RecordForm<DemoRecord>> = {
  title: 'shared/Table/RecordForm',
  component: RecordForm,
  parameters: {
    layout: 'padded',
    backgrounds: { default: 'widget' },
  },
  decorators: [
    // eslint-disable-next-line @typescript-eslint/naming-convention
    (Story) => (
      <div style={{ maxWidth: 600, height: 600, padding: 24, background: '#272727', borderRadius: 12 }}>
        <Story />
      </div>
    ),
  ],
};

export default meta;

type Story = StoryObj<typeof RecordForm<DemoRecord>>;

export const AllInputTypes: Story = {
  args: {
    columns: columns as never,
    initialData,
    mode: 'edit',
    onSubmit: async (data) => {
      // eslint-disable-next-line no-console
      console.log('Form submitted:', data);
      await new Promise((r) => setTimeout(r, 1000));
    },
  },
};

export const EmptyForm: Story = {
  args: {
    columns: columns as never,
    initialData: {
      tags: [],
      coordinates: { lat: 0, lon: 0 },
    },
    mode: 'edit',
  },
};

export const WithValidationErrors: Story = {
  args: {
    columns: columns as never,
    initialData: {
      name: 'Тест',
      quantity: 10,
      status: '1',
      tags: [],
      coordinates: { lat: 55, lon: 37 },
      color: '#FF0000',
      workTime: '10:00',
      modelName: 'Модель',
    },
    mode: 'edit',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);

    const textInputs = canvas.getAllByRole('textbox');
    for (const input of textInputs) {
      if (!(input as HTMLInputElement).disabled && !(input as HTMLInputElement).readOnly) {
        await userEvent.clear(input);
      }
    }

    await userEvent.tab();

    const errors = canvas.getAllByText('Заполните поле');
    await expect(errors.length).toBeGreaterThan(0);
  },
};
