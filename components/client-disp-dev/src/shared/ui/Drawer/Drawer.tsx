import {
  Drawer as MantineDrawer,
  type DrawerBodyProps,
  type DrawerCloseButtonProps,
  type DrawerContentProps,
  type DrawerHeaderProps,
  type DrawerOverlayProps,
  type DrawerProps,
  type DrawerRootProps,
  type DrawerTitleProps,
} from '@mantine/core';

import { Z_INDEX } from '@/shared/lib/constants';

import styles from './Drawer.module.css';

/**
 * Представляет компонент-обертку для выезжающего контейнера.
 */
function Drawer(props: Readonly<DrawerProps>) {
  return <MantineDrawer {...props} />;
}

/**
 * Представляет компонент-обертку для корневого элемента выезжающего контейнера.
 */
function DrawerRoot(props: Readonly<DrawerRootProps>) {
  return (
    <MantineDrawer.Root
      zIndex={Z_INDEX.FIXED}
      classNames={{
        root: styles.root,
        content: styles.content,
        header: styles.header,
        title: styles.title,
        body: styles.body,
      }}
      {...props}
    />
  );
}

/**
 * Представляет компонент-обертку для фонового слоя при появлении выезжающего контейнера.
 */
function DrawerOverlay(props: Readonly<DrawerOverlayProps>) {
  return <MantineDrawer.Overlay {...props} />;
}

/**
 * Представляет компонент-обертку для контента выезжающего контейнера.
 */
function DrawerContent(props: Readonly<DrawerContentProps>) {
  return <MantineDrawer.Content {...props} />;
}

/**
 * Представляет компонент-обертку для контейнера заголовка выезжающего контейнера.
 */
function DrawerHeader(props: Readonly<DrawerHeaderProps>) {
  return <MantineDrawer.Header {...props} />;
}

/**
 * Представляет компонент-обертку для заголовка выезжающего контейнера.
 */
function DrawerTitle(props: Readonly<DrawerTitleProps>) {
  return <MantineDrawer.Title {...props} />;
}

/**
 * Представляет компонент-обертку для кнопки закрытия выезжающего контейнера.
 */
function DrawerCloseButton(props: Readonly<DrawerCloseButtonProps>) {
  return <MantineDrawer.CloseButton {...props} />;
}

/**
 * Представляет компонент-обертку для содержимого выезжающего контейнера.
 */
function DrawerBody(props: Readonly<DrawerBodyProps>) {
  return <MantineDrawer.Body {...props} />;
}

// Присваиваем вложенные компоненты как свойства основного компонента для совместимости с API Mantine
const DrawerWithComponents = Object.assign(Drawer, {
  Root: DrawerRoot,
  Overlay: DrawerOverlay,
  Content: DrawerContent,
  Title: DrawerTitle,
  CloseButton: DrawerCloseButton,
  Header: DrawerHeader,
  Body: DrawerBody,
});

export { DrawerWithComponents as Drawer };
