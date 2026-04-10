import type { FunctionComponent, SVGProps } from 'react';

import { assertHasValue } from '@/shared/lib/assert-has-value';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { type AppRouteType, AppRoutes, getRouteMain, getRouteWorkOrders } from '@/shared/routes/router';

/**
 * Конфигурация секции навигационного меню.
 * Используется для построения сайдбара и мобильного меню.
 */
export interface NavLinks {
  /** Заголовок секции меню */
  readonly title: string;
  /** Иконка, отображаемая рядом с заголовком секции */
  readonly icon?: FunctionComponent<SVGProps<SVGSVGElement>>;
  /** Вложенные элементы навигации (подменю секции) */
  readonly items?: readonly {
    /** Название пункта меню */
    readonly title: string;
    /** Иконка пункта меню */
    readonly icon?: FunctionComponent<SVGProps<SVGSVGElement>>;
    /** Иконка для заголовка страницы в Header */
    readonly headerIcon?: FunctionComponent<SVGProps<SVGSVGElement>>;
    /** URL для перехода. '#' означает, что страница ещё не реализована */
    readonly url: string;
    /** Ключ страницы из AppRoutes */
    readonly key?: AppRouteType;
    /** Скрываем в навигации, можно перейти только по прямой ссылке */
    readonly hiddenInNav?: boolean;
  }[];
}

/**
 * Список навигационных ссылок.
 * Является источником истины для доступов и ролей.
 */
export const navLinks: readonly NavLinks[] = [
  {
    title: 'Основное',
    items: [
      {
        title: 'Главный экран',
        url: getRouteMain(),
        key: AppRoutes.MAIN,
      },
      {
        title: 'Наряд-задания',
        url: getRouteWorkOrders(),
        key: AppRoutes.WORK_ORDERS,
      },
    ],
  },
] as const;

/** Словарь, где ключом является ключ роута, а значением наименование роута. */
export const dictionaryNavLinks = new Map(
  navLinks.flatMap(
    (link) =>
      link.items
        ?.filter((item) => hasValue(item.key))
        .map((item) => {
          assertHasValue(item.key);
          return [item.key, item.title];
        }) ?? EMPTY_ARRAY,
  ),
);

/**
 * Находит элемент навигации и его родительскую секцию по ключу страницы.
 *
 * @param pageKey Ключ страницы из AppRoutes
 * @returns Объект с найденным элементом и секцией, либо {item: null, section: null} если не найдено
 */
export function getItemAndSectionByPageKey(pageKey: string) {
  for (const section of navLinks) {
    const foundItem = section.items?.find((item) => item.key === pageKey);
    if (foundItem) {
      return { item: foundItem, section };
    }
  }
  return { item: null, section: null };
}

/**
 * Возвращает заголовок страницы по её URL.
 *
 * @param url URL-страницы
 * @returns Заголовок страницы или undefined, если страница не найдена
 */
export function getPageTitle(url: string) {
  const { page } = findPageByUrl(url);
  return page?.title;
}

/**
 * Ищет страницу в навигации по URL.
 *
 * @param url URL для поиска
 * @returns Объект с найденной страницей и её родительской секцией
 */
function findPageByUrl(url: string): {
  page?: { title: string; url: string };
  section?: NavLinks;
} {
  for (const section of navLinks) {
    const foundItem = section.items?.find((item) => item.url === url);
    if (foundItem) {
      return { page: foundItem, section };
    }
  }
  return {};
}
