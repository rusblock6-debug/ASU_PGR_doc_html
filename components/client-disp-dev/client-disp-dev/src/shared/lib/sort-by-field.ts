/** Порядок сортировки (по возрастанию или по убыванию). */
export type SortOrder = 'asc' | 'desc';

/**
 * Параметры сортировки: поле и порядок.
 */
export interface SortState<TField extends string = string> {
  /** Имя поля, по которому выполняется сортировка. */
  readonly field: TField;
  /** Порядок сортировки. */
  readonly order: SortOrder;
}

/**
 * Сортирует массив объектов по указанному полю и порядку.
 * Числовые поля сравниваются арифметически, остальные — через localeCompare.
 */
export function sortByField<T>(items: readonly T[], { field, order }: SortState): readonly T[] {
  const sorted = [...items].sort((a, b) => {
    const aRaw = (a as never)[field] ?? '';
    const bRaw = (b as never)[field] ?? '';

    if (typeof aRaw === 'number' && typeof bRaw === 'number') {
      return aRaw - bRaw;
    }

    return String(aRaw).localeCompare(String(bRaw));
  });

  if (order === 'desc') sorted.reverse();
  return sorted;
}

/**
 * Переключает сортировку: при клике на ту же колонку — по возрастанию ←→ по убыванию,
 * при клике на другую — новая колонка с сортировкой по возрастанию.
 */
export function toggleSort<TField extends string>(current: SortState<TField>, field: TField): SortState<TField> {
  if (current.field === field) {
    return { field, order: current.order === 'asc' ? 'desc' : 'asc' };
  }
  return { field, order: 'asc' };
}
