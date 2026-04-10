import { useScrollIntoView } from '@mantine/hooks';
import { useEffect } from 'react';
import { NavLink } from 'react-router-dom';

import { FavoriteButton } from '@/features/favorite-page';
import { PinPageButton } from '@/features/pin-page';

import { cn } from '@/shared/lib/classnames-utils';
import type { NavLinks } from '@/shared/routes/navigation';
import { ScrollArea } from '@/shared/ui/ScrollArea';

import styles from './NavMain.module.css';

/** Cвойства компонента навигации {@link NavMain}. */
interface NavMainProps {
  /** Секции навигации с подпунктами. */
  readonly items: readonly NavLinks[];
  /** Режим отображения: компактный список или блоки. */
  readonly variant?: 'default' | 'block';
  /** Индекс секции для прокрутки в область видимости. */
  readonly selectedSectionIndex?: number | null;
  /** Колбэк после перехода по ссылке. */
  readonly onNavigate?: () => void;
}

/**
 * Основная навигация приложения: секции меню с подпунктами.
 * Используется в сайдбаре, мобильном меню и на главной странице.
 * Элементы с `hiddenInNav: true` не отображаются в списке.
 */
export function NavMain({ items, selectedSectionIndex, variant = 'default', onNavigate }: NavMainProps) {
  const { scrollIntoView, targetRef, scrollableRef } = useScrollIntoView<HTMLLIElement, HTMLDivElement>({
    duration: 100,
  });

  useEffect(() => {
    if (selectedSectionIndex !== null && selectedSectionIndex !== undefined) {
      scrollIntoView({ alignment: 'start' });
    }
  }, [selectedSectionIndex, scrollIntoView]);

  const menuList = (
    <ul className={cn(styles.menu, { [styles.menu_block_variant]: variant === 'block' })}>
      {items.map((item, index, array) => {
        const isLastSection = index === array.length - 1;

        return (
          <li
            key={item.title + index}
            ref={index === selectedSectionIndex ? targetRef : null}
            className={cn(styles.menu_item, { [styles.last_section]: variant === 'default' && isLastSection })}
          >
            <div className={styles.item_header}>
              <div className={styles.item_icon}>{item.icon && <item.icon />}</div>
              <span>{item.title}</span>
            </div>

            {variant === 'block' ? (
              <ScrollArea.Autosize
                mah={550}
                classNames={{ root: styles.item_content }}
                offsetScrollbars={true}
              >
                {item.items
                  ?.filter((subItem) => !subItem.hiddenInNav)
                  .map((subItem) => {
                    return (
                      <div
                        key={subItem.title}
                        className={styles.item_list}
                      >
                        <NavLink
                          to={subItem.url}
                          className={cn(styles.item_link, {
                            [styles.item_link_disabled]: !subItem.url || subItem.url === '#',
                          })}
                          onClick={() => onNavigate?.()}
                        >
                          <span>{subItem.title}</span>
                        </NavLink>
                        {subItem.key && (
                          <div
                            role="presentation"
                            className={styles.button_wrapper}
                            onMouseDown={(e) => e.preventDefault()}
                          >
                            <FavoriteButton
                              tabIndex={-1}
                              className={styles.fav_icon}
                              pageId={subItem.key}
                            />
                          </div>
                        )}
                        {subItem.key && (
                          <div
                            role="presentation"
                            className={styles.button_wrapper}
                            onMouseDown={(e) => e.preventDefault()}
                          >
                            <PinPageButton
                              tabIndex={-1}
                              className={cn(styles.fav_icon, styles.fav_icon_pin)}
                              pageId={subItem.key}
                            />
                          </div>
                        )}
                      </div>
                    );
                  })}
              </ScrollArea.Autosize>
            ) : (
              <ul className={styles.item_content}>
                {item.items
                  ?.filter((subItem) => !subItem.hiddenInNav)
                  .map((subItem) => {
                    return (
                      <li
                        key={subItem.title}
                        className={styles.item_list}
                      >
                        <NavLink
                          to={subItem.url}
                          className={cn(styles.item_link, {
                            [styles.item_link_disabled]: !subItem.url || subItem.url === '#',
                          })}
                          onClick={() => onNavigate?.()}
                        >
                          <span>{subItem.title}</span>
                        </NavLink>
                        {subItem.key && (
                          <div
                            role="presentation"
                            className={styles.button_wrapper}
                            onMouseDown={(e) => e.preventDefault()}
                          >
                            <FavoriteButton
                              tabIndex={-1}
                              className={styles.fav_icon}
                              pageId={subItem.key}
                            />
                          </div>
                        )}
                        {subItem.key && (
                          <div
                            role="presentation"
                            className={styles.button_wrapper}
                            onMouseDown={(e) => e.preventDefault()}
                          >
                            <PinPageButton
                              tabIndex={-1}
                              className={cn(styles.fav_icon, styles.fav_icon_pin)}
                              pageId={subItem.key}
                            />
                          </div>
                        )}
                      </li>
                    );
                  })}
              </ul>
            )}
          </li>
        );
      })}
    </ul>
  );

  return variant === 'default' ? (
    <ScrollArea.Autosize
      mah="100vh"
      viewportRef={scrollableRef}
    >
      {menuList}
    </ScrollArea.Autosize>
  ) : (
    menuList
  );
}
