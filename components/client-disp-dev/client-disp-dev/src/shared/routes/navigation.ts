import type { FunctionComponent, SVGProps } from 'react';

import FleetControlIcon from '@/shared/assets/icons/fav-fleet-control.svg?react';
import KrvIcon from '@/shared/assets/icons/fav-krv.svg?react';
import MapIcon from '@/shared/assets/icons/fav-map.svg?react';
import TripIcon from '@/shared/assets/icons/fav-trip.svg?react';
import WorkOrderIcon from '@/shared/assets/icons/fav-work-order.svg?react';
import ChartIcon from '@/shared/assets/icons/ic-chart-fill.svg?react';
import FleetControlPageIcon from '@/shared/assets/icons/ic-page-fleet-control.svg?react';
import MapPageIcon from '@/shared/assets/icons/ic-page-map.svg?react';
import WorkOrderPageIcon from '@/shared/assets/icons/ic-page-work-order.svg?react';
import WorkTimeMapPageIcon from '@/shared/assets/icons/ic-page-work-time-map.svg?react';
import PaperworkIcon from '@/shared/assets/icons/ic-paperwork.svg?react';
import SettingsIcon from '@/shared/assets/icons/ic-settings-fill.svg?react';
import ShieldIcon from '@/shared/assets/icons/ic-shield.svg?react';
import UnionIcon from '@/shared/assets/icons/union.svg?react';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import {
  type AppRouteType,
  AppRoutes,
  getRouteEquipment,
  getRouteMap,
  getRoutePlaces,
  getRouteTripEditor,
  getRouteWorkOrder,
  getRouteWorkTimeMap,
  getRouteHorizons,
  getRouteStatuses,
  getRouteSections,
  getRouteTags,
  getRouteCargo,
  getRouteDispatchMap,
  getRouteStaff,
  getRouteRoles,
  getRouteFleetControl,
} from '@/shared/routes/router';

/**
 * Конфигурация секции навигационного меню.
 * Используется для построения сайдбара и мобильного меню.
 */
export interface NavLinks {
  /** Заголовок секции меню (например, "Оперативная работа", "Отчеты") */
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
    /** Ключ страницы из AppRoutes для идентификации в избранном (FavoriteButton) и закреплённых страницах (PinPageButton) */
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
    title: 'Оперативная работа',
    icon: UnionIcon,
    items: [
      {
        title: 'Рапорт диспетчера',
        url: '#',
      },
      {
        title: 'Управление техникой',
        url: getRouteFleetControl(),
        icon: FleetControlIcon,
        headerIcon: FleetControlPageIcon,
        key: AppRoutes.FLEET_CONTROL,
      },
      {
        title: 'Карта',
        url: getRouteMap(),
        icon: MapIcon,
        headerIcon: MapPageIcon,
        key: AppRoutes.MAP,
      },
      {
        title: 'Карта (2D)',
        url: getRouteDispatchMap(),
        icon: MapIcon,
        headerIcon: MapPageIcon,
        key: AppRoutes.DISPATCH_MAP,
      },
      {
        title: 'КРВ (Карта рабочего времени)',
        icon: KrvIcon,
        headerIcon: WorkTimeMapPageIcon,
        url: getRouteWorkTimeMap(),
        key: AppRoutes.WORK_TIME_MAP,
      },
      {
        title: 'Управление рейсами',
        icon: TripIcon,
        url: getRouteTripEditor(),
        key: AppRoutes.TRIP_EDITOR,
      },
      {
        title: 'Наряд-задание',
        icon: WorkOrderIcon,
        headerIcon: WorkOrderPageIcon,
        url: getRouteWorkOrder(),
        key: AppRoutes.WORK_ORDER,
      },
      {
        title: 'Планирование работ',
        url: '#',
      },
      {
        title: 'Планирование БВР',
        url: '#',
      },
      {
        title: 'Редактор смен',
        url: '#',
      },
    ],
  },
  {
    title: 'Отчеты',
    icon: ChartIcon,
    items: [
      {
        title: 'Сменная статистика для оборудования',
        url: '#',
      },
      {
        title: 'Эффективность техники',
        url: '#',
      },
      {
        title: 'Лог действий пользователей',
        url: '#',
      },
      {
        title: 'Архив сообщений',
        url: '#',
      },
    ],
  },
  {
    title: 'Справочники',
    icon: PaperworkIcon,
    items: [
      // Временно скрыли для демо 23.12.2025 узнать у Марата когда вернуть
      // {
      //   title: 'Рудники',
      //   url: '#',
      // },
      {
        title: 'Горизонты',
        url: getRouteHorizons(),
        key: AppRoutes.HORIZONS,
      },
      {
        title: 'Места',
        url: getRoutePlaces(),
        key: AppRoutes.PLACES,
      },
      {
        title: 'Участки',
        url: getRouteSections(),
        key: AppRoutes.SECTIONS,
      },
      {
        title: 'Метки',
        url: getRouteTags(),
        key: AppRoutes.TAGS,
      },
      {
        title: 'Персонал',
        url: getRouteStaff(),
        key: AppRoutes.STAFF,
      },
      {
        title: 'Роли',
        url: getRouteRoles(),
        key: AppRoutes.ROLES,
      },
      {
        title: 'Оборудование',
        url: getRouteEquipment(),
        key: AppRoutes.EQUIPMENT,
      },
      {
        title: 'Статусы',
        url: getRouteStatuses(),
        key: AppRoutes.STATUSES,
      },
      {
        title: 'Виды груза',
        url: getRouteCargo(),
        key: AppRoutes.CARGO,
      },
      // Временно скрыли для демо 23.12.2025 узнать у Марата когда вернуть
      // {
      //   title: 'Виды работ',
      //   url: '#',
      // },
    ],
  },
  {
    title: 'Диагностика',
    icon: ShieldIcon,
    items: [
      {
        title: 'Оборудование',
        url: '#',
      },
      {
        title: 'Система',
        url: '#',
      },
    ],
  },
  {
    title: 'Настройки',
    icon: SettingsIcon,
    items: [
      {
        title: 'Предприятие',
        url: '#',
      },
      {
        title: 'Система',
        url: '#',
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
