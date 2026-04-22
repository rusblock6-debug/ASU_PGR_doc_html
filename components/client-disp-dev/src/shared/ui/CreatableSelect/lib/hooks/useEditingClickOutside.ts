import { useClickOutside } from '@mantine/hooks';
import { useRef } from 'react';

/**
 * Хук для обработки клика вне компонента при редактировании.
 */
export function useEditingClickOutside(onFinish: () => void | Promise<void>) {
  const onFinishRef = useRef(onFinish);
  onFinishRef.current = onFinish;

  return useClickOutside<HTMLDivElement>(() => {
    onFinishRef.current();
  });
}
