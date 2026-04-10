import type { ReactNode } from 'react';
import { useSyncExternalStore } from 'react';

let content: ReactNode = null;
const listeners = new Set<() => void>();

/**
 * Управление тултипом карты — показ, скрытие и подписка на контент.
 *
 * Есть проблема внутри `<Canvas>` R3F — отдельное React-дерево без `MantineProvider`,
 * поэтому Mantine-компоненты (Tooltip, Popover и т.д.) там не работают.
 *
 * Чтобы решить эту проблему создан отдельный стор — маркер на карте при наведении вызывает `tooltipStore.show(...)`,
 * а оверлей подписан через хук `useTooltipContent()` и сразу получает контент.
 */
export const tooltipStore = {
  show(value: ReactNode) {
    content = value;
    emitListeners();
  },

  hide() {
    content = null;
    emitListeners();
  },

  subscribe(listener: () => void) {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },

  // eslint-disable-next-line sonarjs/function-return-type
  getSnapshot() {
    return content;
  },
};

/**
 * Оповещает подписчиков об изменении контента.
 */
function emitListeners() {
  listeners.forEach((listener) => listener());
}

/**
 * Возвращает текущий контент тултипа; перерисовывает компонент при каждом `show` / `hide`.
 */
// eslint-disable-next-line sonarjs/function-return-type
export function useTooltipContent() {
  return useSyncExternalStore(tooltipStore.subscribe, tooltipStore.getSnapshot);
}
