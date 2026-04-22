/**
 * Создает объект конфигурации маршрута с ключом и функцией генерации пути
 *
 * @template TParams - Типы параметров для функции генерации пути
 * @param key - Уникальный ключ маршрута
 * @param pathFn - Функция для генерации пути маршрута
 * @returns Объект конфигурации с полями KEY и PATH
 * @example
 * const mainRoute = createRoute('main', () => '/');
 * const settingsRoute = createRoute('settings', (id: string) => `/settings/${id}`);
 */
export function createRoute<Key extends string, TParams extends unknown[] = []>(
  key: Key,
  pathFn: (...args: TParams) => string,
) {
  return {
    KEY: key,
    PATH: pathFn,
  };
}
