import { cloneElement, isValidElement, useMemo, useState } from 'react';
import type { Layout } from 'react-grid-layout';
import { Responsive, WidthProvider } from 'react-grid-layout';

/**
 * ВАЖНО: Осознанное нарушение FSD архитектуры
 *
 * WorkspacePage импортирует routeConfig из app/providers/router для отображения
 * других страниц в виде виджетов. Это временное решение для ускорения разработки.
 *
 * ПРАВИЛЬНОЕ решение по FSD:
 * - Создать отдельные widgets для каждой страницы (например, widgets/main-content)
 * - MainPage и WorkspacePage будут использовать один и тот же виджет
 * - Это обеспечит правильную изоляцию слоев
 *
 * Текущее решение допустимо, так как:
 * - WorkspacePage имеет уникальную задачу - отображать другие страницы
 * - Используем клонирование элементов для изоляции состояния
 */
/* eslint-disable-next-line fsd/forbidden-imports */
import { routeConfig } from '@/app/providers/router';

import { Page } from '@/widgets/page-layout';

import { GRID_COLS, type PinnedPage, usePinnedPages } from '@/features/pin-page';

import { cn } from '@/shared/lib/classnames-utils';
import { WorkspaceProvider } from '@/shared/lib/workspace';

import { Empty } from '../Empty';
import { PageWidget } from '../PageWidget';

import styles from './WorkspacePage.module.css';

const ResponsiveGridLayout = WidthProvider(Responsive);

/**
 * Представляет компонент страницы «Рабочая область».
 */
export function WorkspacePage() {
  const { pinnedPages, updateLayout } = usePinnedPages();
  const [isDragging, setIsDragging] = useState(false);

  const layouts = useMemo(() => {
    return {
      lg: pinnedPages.map((page: PinnedPage) => ({
        i: page.id,
        x: page.layout.x,
        y: page.layout.y,
        w: page.layout.w,
        h: page.layout.h,
        minW: 1,
        minH: 1,
      })),
    };
  }, [pinnedPages]);

  const handleLayoutChange = (currentLayout: Layout[]) => {
    if (currentLayout.length === 0) return;

    const newLayouts = currentLayout.map((item) => ({
      x: item.x,
      y: item.y,
      w: item.w,
      h: item.h,
    }));

    updateLayout(newLayouts);
  };

  if (pinnedPages.length === 0) {
    return (
      <Page className={styles.page}>
        <Empty />
      </Page>
    );
  }

  return (
    <ResponsiveGridLayout
      className={cn(styles.grid_layout, { [styles.dragging]: isDragging })}
      layouts={layouts}
      breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
      cols={{ lg: GRID_COLS, md: GRID_COLS, sm: GRID_COLS, xs: GRID_COLS, xxs: GRID_COLS }}
      rowHeight={150}
      margin={[1, 1]}
      onLayoutChange={handleLayoutChange}
      onDragStart={() => setIsDragging(true)}
      onDragStop={() => setIsDragging(false)}
      onResizeStart={() => setIsDragging(true)}
      onResizeStop={() => setIsDragging(false)}
      isDraggable
      isResizable
      draggableHandle=".js-workspace-drag-handle"
      resizeHandles={['s', 'w', 'e', 'n', 'sw', 'nw', 'se', 'ne']}
    >
      {pinnedPages.map((page: PinnedPage) => {
        const routeElement = routeConfig[page.route]?.element;

        if (!routeElement || !isValidElement(routeElement)) {
          return (
            <div key={page.id}>
              <PageWidget page={page}>
                <div>Страница не найдена</div>
              </PageWidget>
            </div>
          );
        }

        return (
          <div key={page.id}>
            <WorkspaceProvider value={true}>{cloneElement(routeElement, { key: page.id })}</WorkspaceProvider>
          </div>
        );
      })}
    </ResponsiveGridLayout>
  );
}
