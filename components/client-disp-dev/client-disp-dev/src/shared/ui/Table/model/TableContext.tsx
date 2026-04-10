import { createContext, type PropsWithChildren, useCallback, useContext, useMemo, useState } from 'react';

import { deleteWithToast } from '../lib/table-actions';
import type { ColumnDef } from '../types';

export type DrawerMode = 'closed' | 'add' | 'edit';

interface TableContextValue<TData> {
  /** Колонки таблицы */
  columns: ColumnDef<TData>[];
  /** Исходные данные */
  data: readonly TData[];
  /** Колбэк для получения идентификатора ряда. */
  getRowId: (row: TData) => string | number;
  /** Сколько всего объектов */
  total?: number;
  /** Отфильтрованные данные */
  filteredData: readonly TData[];
  /** Поисковый запрос */
  searchQuery: string;
  /** Установить поисковый запрос */
  setSearchQuery: (query: string) => void;

  /** Выбранные строки */
  selectedRows: TData[];
  /** Установить выбранные строки */
  setSelectedRows: (rows: TData[]) => void;
  /** Callback при изменении выбора строк (из TanStack Table) */
  onRowSelectionChange?: (selectedRowIds: Record<string, boolean>) => void;

  /** Режим drawer: 'closed' | 'add' | 'edit' */
  drawerMode: DrawerMode;
  /** Редактируемая строка (для режима edit) */
  editingRow: TData | null;
  /** Открыть drawer для добавления */
  openAddDrawer: () => void;
  /** Открыть drawer для редактирования */
  openEditDrawer: (row: TData) => void;
  /** Закрыть drawer */
  closeDrawer: () => void;

  /** Callback для добавления записи */
  onAdd?: (newRecord: Partial<TData>) => void | Promise<void>;
  /** Callback для редактирования записи */
  onEdit?: (id: string | number, data: Partial<TData>) => void | Promise<void>;
  /** Callback для удаления записей */
  onDelete?: (ids: (string | number)[]) => void | Promise<void>;

  /** Ключ для сохранения состояния таблицы в LocalStorage */
  storageKey?: string;

  /** Заголовок формы для режима добавления */
  formAddTitle?: string;
  /** Заголовок формы для режима редактирования */
  formEditTitle?: string;
}

interface TableProviderProps<TData> {
  /** Данные для таблицы. */
  readonly data: readonly TData[];
  /** Колонки. */
  readonly columns: ColumnDef<TData>[];
  /** Возвращает идентификатор строки. */
  readonly getRowId: (row: TData) => string | number;
  /** Общее количество элементов. */
  readonly total?: number;
  /** Обработчик добавления. */
  readonly onAdd?: (newRecord: Partial<TData>) => void | Promise<void>;
  /** Обработчик редактирования. */
  readonly onEdit?: (id: string | number, data: Partial<TData>) => void | Promise<void>;
  /** Обработчик удаления.*/
  readonly onDelete?: (ids: (string | number)[]) => void | Promise<void>;
  /** Ключ для local storage. */
  readonly storageKey?: string;
  /** Заголовок формы добавления. */
  readonly formAddTitle?: string;
  /** Заголовок формы редактирования. */
  readonly formEditTitle?: string;
  /** Обработчик режима добавления. */
  readonly onAddMode?: () => void;
  /** Обработчик режима редактирования. */
  readonly onEditMode?: (row: TData) => void;
  /** Обработчик закрытия сайдбара. */
  readonly onCloseDrawer?: () => void;
  /** Обработчик выбора строк. */
  readonly onSelectRow?: (rows: readonly TData[]) => void;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const TableContext = createContext<TableContextValue<any> | null>(null);

export function TableProvider<TData>({
  data,
  columns,
  getRowId,
  total,
  onAdd,
  onEdit,
  onDelete,
  storageKey,
  formAddTitle = 'Новый объект',
  formEditTitle = 'Редактировать объект',
  onAddMode,
  onEditMode,
  onCloseDrawer,
  onSelectRow,
  children,
}: PropsWithChildren<TableProviderProps<TData>>) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRows, setSelectedRows] = useState<TData[]>([]);
  const [drawerMode, setDrawerMode] = useState<DrawerMode>('closed');
  const [editingRow, setEditingRow] = useState<TData | null>(null);

  // Фильтрация данных по поисковому запросу
  const filteredData = useMemo(() => {
    if (!searchQuery.trim()) {
      return data;
    }

    const lowerQuery = searchQuery.toLowerCase();

    return data.filter((row) =>
      columns.some((col) => {
        // Игнорируем служебные колонки
        if (col.id === 'select' || col.meta?.dummyElement) {
          return false;
        }

        // Получаем значение ячейки
        let value: unknown;
        if ('accessorKey' in col && col.accessorKey) {
          value = row[col.accessorKey as keyof TData];
        } else if ('accessorFn' in col && col.accessorFn) {
          value = col.accessorFn(row, 0);
        }

        // Проверяем, содержит ли значение поисковый запрос
        if (value != null) {
          return String(value).toLowerCase().includes(lowerQuery);
        }

        return false;
      }),
    );
  }, [data, searchQuery, columns]);

  // Синхронизация для выбранных рядов (чекбоксы)
  const onRowSelectionChange = (selectedRowIds: Record<string, boolean>) => {
    const selectedData = data.filter((_, index) => selectedRowIds[index]);
    setSelectedRows(selectedData);
    onSelectRow?.(selectedData);
  };

  const openAddDrawer = () => {
    setDrawerMode('add');
    setEditingRow(null);
    onAddMode?.();
  };

  const openEditDrawer = (row: TData) => {
    setDrawerMode('edit');
    setEditingRow(row);
    onEditMode?.(row);
  };

  const closeDrawer = () => {
    setDrawerMode('closed');
    setEditingRow(null);
    onCloseDrawer?.();
  };

  const wrappedOnDelete = useCallback(
    async (ids: (string | number)[]) => {
      if (!onDelete) return;
      await deleteWithToast(onDelete(ids), ids.length);
      onSelectRow?.([]);
    },
    [onDelete, onSelectRow],
  );

  const value: TableContextValue<TData> = {
    columns,
    data,
    getRowId,
    total,
    filteredData,
    searchQuery,
    setSearchQuery,
    storageKey,

    // Row selection
    selectedRows,
    setSelectedRows,
    onRowSelectionChange,

    // Drawer state
    drawerMode,
    editingRow,
    openAddDrawer,
    openEditDrawer,
    closeDrawer,
    formAddTitle,
    formEditTitle,

    // CRUD callbacks
    onAdd,
    onEdit,
    onDelete: onDelete ? wrappedOnDelete : undefined,
  };

  return <TableContext.Provider value={value}>{children}</TableContext.Provider>;
}

export function useTableContext<TData>(): TableContextValue<TData> {
  const context = useContext(TableContext);
  if (!context) {
    throw new Error('useTableContextStrict must be used within TableProvider');
  }
  return context;
}
