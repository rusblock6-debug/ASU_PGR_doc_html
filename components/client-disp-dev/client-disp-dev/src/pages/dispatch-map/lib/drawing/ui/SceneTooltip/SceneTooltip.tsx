import { Html } from '@react-three/drei';
import type { PointerEvent, PropsWithChildren } from 'react';

import styles from './SceneTooltip.module.css';

/**
 * Представляет свойства компонента {@link SceneTooltip}.
 */
interface SceneTooltipProps {
  /** Позиция в сцене [x, y, z]. */
  readonly position: [number, number, number];
}

/**
 * Контейнер-попап, привязанный к позиции в 3D-сцене.
 *
 * Оборачивает дочерние элементы в `Html` из drei и добавляет общую стилизацию.
 */
export function SceneTooltip({ position, children }: PropsWithChildren<SceneTooltipProps>) {
  return (
    <Html
      position={position}
      center
      className={styles.wrapper}
      zIndexRange={[10, 10]}
    >
      <div className={styles.tooltip}>{children}</div>
    </Html>
  );
}

/**
 * Представляет свойства компонента {@link TooltipButton}.
 */
interface TooltipButtonProps {
  /** Текст всплывающей подсказки (`data-tooltip`). */
  readonly tooltip: string;
  /** Обработчик клика. */
  readonly onClick: () => void;
}

/**
 * Кнопка с тултипом внутри {@link SceneTooltip}.
 *
 * Блокирует всплытие `pointerdown`, чтобы клик по кнопке
 * не перехватывался OrbitControls или drag-логикой сцены.
 */
export function TooltipButton({ tooltip, onClick, children }: PropsWithChildren<TooltipButtonProps>) {
  const handlePointerDown = (event: PointerEvent) => event.stopPropagation();

  return (
    <button
      type="button"
      data-tooltip={tooltip}
      className={styles.button}
      onPointerDown={handlePointerDown}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
