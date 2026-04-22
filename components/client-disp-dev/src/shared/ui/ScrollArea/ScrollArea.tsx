import { ScrollArea as MantineScrollArea, ScrollAreaAutosize as MantineScrollAreaAutosize } from '@mantine/core';
import type {
  ScrollAreaProps as MantineScrollAreaProps,
  ScrollAreaAutosizeProps as MantineScrollAreaAutosizeProps,
} from '@mantine/core';

import { cn } from '@/shared/lib/classnames-utils';

import styles from './ScrollArea.module.css';

/** Дефолтный размер скроллбара */
const DEFAULT_SCROLLBAR_SIZE = 8;

/** Имена стилей ScrollArea */
type ScrollAreaStylesNames = 'root' | 'viewport' | 'scrollbar' | 'thumb' | 'corner';

/** Типы пропсов с classNames только как объект (без функций) */
type ScrollAreaProps = Omit<MantineScrollAreaProps, 'classNames'> & {
  readonly classNames?: Partial<Record<ScrollAreaStylesNames, string>>;
};

/** Типы пропсов с classNames только как объект (без функций) */
type ScrollAreaAutosizeProps = Omit<MantineScrollAreaAutosizeProps, 'classNames'> & {
  readonly classNames?: Partial<Record<ScrollAreaStylesNames, string>>;
};

/** Классы для кастомного оформления скроллбара */
const defaultClassNames: Record<ScrollAreaStylesNames, string> = {
  root: styles.root,
  scrollbar: styles.scrollbar,
  thumb: styles.thumb,
  corner: styles.corner,
  viewport: styles.viewport,
};

/**
 * ScrollArea - адаптер для Mantine ScrollArea
 * Обеспечивает единый интерфейс для компонента прокрутки в приложении
 * По умолчанию: type="auto", offsetScrollbars=true, scrollbarSize=8
 *
 * Кастомные стили скроллбара применяются только когда type !== 'never'
 */
function ScrollArea({
  className,
  classNames,
  style,
  children,
  type = 'auto',
  offsetScrollbars = true,
  scrollbarSize = DEFAULT_SCROLLBAR_SIZE,
  ...props
}: ScrollAreaProps) {
  const shouldApplyCustomStyles = type !== 'never';

  return (
    <MantineScrollArea
      classNames={
        shouldApplyCustomStyles
          ? {
              ...defaultClassNames,
              ...classNames,
              root: cn(defaultClassNames.root, classNames?.root, className),
            }
          : classNames
      }
      style={{ ...style, '--sa-scrollbar-size': `${scrollbarSize}px` }}
      type={type}
      offsetScrollbars={offsetScrollbars}
      scrollbarSize={scrollbarSize}
      data-scroll-type={type}
      {...props}
    >
      {children}
    </MantineScrollArea>
  );
}

/**
 * ScrollAreaAutosize - адаптер для Mantine ScrollArea.Autosize
 * Автоматически подстраивается под размер контента до максимальной высоты
 * По умолчанию: type="auto", offsetScrollbars=true, scrollbarSize=8
 *
 * Кастомные стили скроллбара применяются только когда type !== 'never'
 */
function ScrollAreaAutosize({
  className,
  classNames,
  style,
  children,
  type = 'auto',
  offsetScrollbars = true,
  scrollbarSize = DEFAULT_SCROLLBAR_SIZE,
  ...props
}: ScrollAreaAutosizeProps) {
  const shouldApplyCustomStyles = type !== 'never';

  return (
    <MantineScrollAreaAutosize
      classNames={
        shouldApplyCustomStyles
          ? {
              ...defaultClassNames,
              ...classNames,
              root: cn(defaultClassNames.root, classNames?.root, className),
              content: styles.content,
            }
          : classNames
      }
      style={{ ...style, '--sa-scrollbar-size': `${scrollbarSize}px` }}
      type={type}
      offsetScrollbars={offsetScrollbars}
      scrollbarSize={scrollbarSize}
      data-scroll-type={type}
      {...props}
    >
      {children}
    </MantineScrollAreaAutosize>
  );
}

// Присваиваем Autosize как свойство основного компонента для совместимости с API Mantine
const ScrollAreaWithAutosize = Object.assign(ScrollArea, {
  Autosize: ScrollAreaAutosize,
});

export { ScrollAreaWithAutosize as ScrollArea, ScrollAreaAutosize };
