import {
  FloatingIndicator as MantineFloatingIndicator,
  type FloatingIndicatorProps as MantineFloatingIndicatorProps,
} from '@mantine/core';

/**
 * Адаптер компонента FloatingIndicator из Mantine.
 *
 * Отображает плавающий индикатор поверх целевого элемента внутри родительского контейнера.
 * Используется для создания кастомных табов, сегментированных контролов и аналогичных UI-элементов.
 *
 * @see https://mantine.dev/core/floating-indicator/
 */
export function FloatingIndicator(props: Readonly<MantineFloatingIndicatorProps>) {
  return <MantineFloatingIndicator {...props} />;
}
