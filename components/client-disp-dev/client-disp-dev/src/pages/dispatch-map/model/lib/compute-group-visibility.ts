/**
 * Состояния видимости группы элементов:
 * - `visible` — все элементы видимы;
 * - `hidden` — все элементы скрыты;
 * - `partial` — элементы видимы частично.
 */
export const GroupVisibility = {
  VISIBLE: 'visible',
  HIDDEN: 'hidden',
  PARTIAL: 'partial',
} as const;

/** Типы значений видимости группы. */
export type GroupVisibilityValue = (typeof GroupVisibility)[keyof typeof GroupVisibility];

/**
 * Вычисляет видимость группы элементов.
 *
 * Логика работы:
 * - Пустая группа считается видимой.
 * - Если все элементы скрыты — `hidden`.
 * - Если все элементы видимы — `visible`.
 * - Если есть и скрытые, и видимые — `partial`.
 */
export function computeGroupVisibility(itemIds: readonly number[], hiddenIds: readonly number[]) {
  if (itemIds.length === 0) return GroupVisibility.VISIBLE;

  let hasVisible = false;
  let hasHidden = false;

  for (const id of itemIds) {
    if (hiddenIds.includes(id)) {
      hasHidden = true;
    } else {
      hasVisible = true;
    }
    if (hasVisible && hasHidden) return GroupVisibility.PARTIAL;
  }

  return hasHidden ? GroupVisibility.HIDDEN : GroupVisibility.VISIBLE;
}
