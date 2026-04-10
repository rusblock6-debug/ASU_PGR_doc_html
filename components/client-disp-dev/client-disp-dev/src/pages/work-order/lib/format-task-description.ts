import type { SelectOption } from '@/shared/ui/types';

import type { RouteTaskDraft } from '../model/types';

/**
 * Форматирует и возвращает описание задания.
 *
 * Собирает непустые части задания (тип, объём, маршрут) и объединяет их через запятую в кавычках.
 * Если все поля пустые, возвращает пустую строку.
 *
 * @returns Отформатированная строка с описанием задания в кавычках или пустая строка.
 *
 * @example
 * // Полное задание
 * formatTaskDescription(task, options)
 * // => "«Перевозка, объём 50 м³, Место А — Место Б»"
 *
 * @example
 * // Только тип и маршрут (без объёма)
 * formatTaskDescription(task, options)
 * // => "«Перевозка, Место А — Место Б»"
 *
 * @example
 * // Только одно место в маршруте
 * formatTaskDescription(task, options)
 * // => "«Перевозка, объём 30 м³, Место А»"
 *
 * @example
 * // Все поля пустые или ID не найдены в справочниках
 * formatTaskDescription(task, options)
 * // => ""
 */
export function formatTaskDescription(
  task: RouteTaskDraft,
  options: {
    readonly taskTypeOptions: readonly SelectOption[];
    readonly placeLoadOptions: readonly SelectOption[];
    readonly placeUnloadOptions: readonly SelectOption[];
  },
) {
  const parts: string[] = [];

  // Тип задания
  const taskType = options.taskTypeOptions.find((opt) => opt.value === task.taskType);
  if (taskType?.label) {
    parts.push(taskType.label);
  }

  // Объём
  if (task.volume) {
    parts.push(`объём ${task.volume} м³`);
  }

  // Маршрут: "Место А — Место Б"
  const startPlace = options.placeLoadOptions.find((place) => place.value === String(task.placeStartId));
  const endPlace = options.placeUnloadOptions.find((place) => place.value === String(task.placeEndId));

  const route = [startPlace?.label, endPlace?.label].filter(Boolean).join(' — ');
  if (route) {
    parts.push(route);
  }

  return parts.length > 0 ? `«${parts.join(', ')}»` : '';
}
