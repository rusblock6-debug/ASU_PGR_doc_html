import type { PageLayout, PinnedPage } from '../model/types/pinned';

export const GRID_COLS = 24;
const DEFAULT_WIDTH = GRID_COLS / 2;
const DEFAULT_HEIGHT = GRID_COLS / 2;

/**
 * Применяет дефолтную схему размещения для 1-4 элементов
 *
 * Правило:
 * - 1 элемент: весь экран (12x6)
 * - 2 элемента: по половине экрана (6x6 каждый)
 * - 3 элемента: первые два сверху (6x3), третий снизу на весь экран (12x3)
 * - 4 элемента: сетка 2x2 (каждый 6x3)
 */
export function applyDefaultLayout(pages: PinnedPage[]): PinnedPage[] {
  if (pages.length === 0) return [];

  if (pages.length === 1) {
    // 1 элемент - весь экран
    return [
      {
        ...pages[0],
        layout: { x: 0, y: 0, w: GRID_COLS, h: DEFAULT_HEIGHT },
      },
    ];
  }

  if (pages.length === 2) {
    // 2 элемента - по половине экрана
    return [
      {
        ...pages[0],
        layout: { x: 0, y: 0, w: DEFAULT_WIDTH, h: DEFAULT_HEIGHT },
      },
      {
        ...pages[1],
        layout: { x: DEFAULT_WIDTH, y: 0, w: DEFAULT_WIDTH, h: DEFAULT_HEIGHT },
      },
    ];
  }

  if (pages.length === 3) {
    // 3 элемента - два сверху, один снизу на весь экран
    return [
      {
        ...pages[0],
        layout: { x: 0, y: 0, w: DEFAULT_WIDTH, h: 3 },
      },
      {
        ...pages[1],
        layout: { x: DEFAULT_WIDTH, y: 0, w: DEFAULT_WIDTH, h: 3 },
      },
      {
        ...pages[2],
        layout: { x: 0, y: 3, w: GRID_COLS, h: 3 },
      },
    ];
  }

  if (pages.length === 4) {
    // 4 элемента - сетка 2x2
    return [
      {
        ...pages[0],
        layout: { x: 0, y: 0, w: DEFAULT_WIDTH, h: 3 },
      },
      {
        ...pages[1],
        layout: { x: DEFAULT_WIDTH, y: 0, w: DEFAULT_WIDTH, h: 3 },
      },
      {
        ...pages[2],
        layout: { x: 0, y: 3, w: DEFAULT_WIDTH, h: 3 },
      },
      {
        ...pages[3],
        layout: { x: DEFAULT_WIDTH, y: 3, w: DEFAULT_WIDTH, h: 3 },
      },
    ];
  }

  // Для 5+ элементов возвращаем как есть (это случай когда уже были ручные изменения)
  return pages;
}

/**
 * Проверяет, отличается ли текущий layout от дефолтной схемы
 */
export function hasManualChanges(pages: PinnedPage[]): boolean {
  if (pages.length === 0 || pages.length > 4) return true;

  const defaultPages = applyDefaultLayout(pages);

  return pages.some((page, index) => {
    const defaultLayout = defaultPages[index].layout;
    const currentLayout = page.layout;

    return (
      defaultLayout.x !== currentLayout.x ||
      defaultLayout.y !== currentLayout.y ||
      defaultLayout.w !== currentLayout.w ||
      defaultLayout.h !== currentLayout.h
    );
  });
}

/**
 * Вычисляет layout для нового виджета (добавляется вниз)
 *
 * @param existingPages - существующие страницы
 */
export function calculateNewLayout(existingPages: PinnedPage[]): PageLayout {
  if (existingPages.length === 0) {
    return { x: 0, y: 0, w: GRID_COLS, h: DEFAULT_HEIGHT };
  }

  // Находим максимальную занятую высоту
  const maxY = Math.max(...existingPages.map((p) => p.layout.y + p.layout.h));

  // Если были ручные изменения - добавляем вниз на всю ширину
  if (hasManualChanges(existingPages)) {
    return { x: 0, y: maxY, w: GRID_COLS, h: 3 };
  }

  // Иначе добавляем вниз сеткой 2 колонки
  const index = existingPages.length;
  const col = index % 2;

  return { x: col * DEFAULT_WIDTH, y: maxY, w: DEFAULT_WIDTH, h: 3 };
}
