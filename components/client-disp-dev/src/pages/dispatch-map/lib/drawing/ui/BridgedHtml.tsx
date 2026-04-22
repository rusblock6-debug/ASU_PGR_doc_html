import { Html } from '@react-three/drei';
import type { HtmlProps } from '@react-three/drei/web/Html';
import { useContextBridge } from 'its-fine';
import type { PropsWithChildren } from 'react';

/**
 * Обёртка над drei {@link Html} с пробросом React-контекстов из основного дерева.
 *
 * `Html` из drei создаёт отдельный React root (`ReactDOM.createRoot`),
 * из-за чего контексты основного приложения (MantineProvider, Redux и др.)
 * недоступны внутри. Этот компонент использует `useContextBridge` из `its-fine`,
 * чтобы автоматически прокинуть все контексты.
 *
 * Использовать вместо `Html` только там, где children содержат
 * Mantine-компоненты или другие элементы, зависящие от провайдеров
 * основного дерева. Для простых тултипов с кастомной вёрсткой
 * достаточно обычного `Html` / {@link SceneTooltip}.
 */
export function BridgedHtml({ children, ...props }: PropsWithChildren<HtmlProps>) {
  const Bridge = useContextBridge();

  return (
    <Html {...props}>
      <Bridge>{children}</Bridge>
    </Html>
  );
}
