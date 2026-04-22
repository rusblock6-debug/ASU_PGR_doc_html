import { useEffect } from 'react';

/**
 * Хук для управления title документа.
 * При размонтировании компонента восстанавливает предыдущий title.
 *
 * @param title - Заголовок страницы
 */
export function useDocumentTitle(title: string) {
  useEffect(() => {
    const prevTitle = document.title;
    document.title = title;

    return () => {
      document.title = prevTitle;
    };
  }, [title]);
}
