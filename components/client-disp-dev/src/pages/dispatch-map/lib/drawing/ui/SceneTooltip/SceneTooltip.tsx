import { Html } from '@react-three/drei';
import type { PointerEvent, PropsWithChildren } from 'react';
import type { Vector3Tuple } from 'three';

import { MAP_SCENE } from '../../../../config/map-scene';
import { BridgedHtml } from '../BridgedHtml';

import styles from './SceneTooltip.module.css';

/**
 * Представляет свойства компонента {@link SceneTooltip}.
 */
interface SceneTooltipProps {
  /** Позиция в сцене [x, y, z]. */
  readonly position: Vector3Tuple;
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
      zIndexRange={[MAP_SCENE.TOOLTIP_Y, MAP_SCENE.TOOLTIP_Y]}
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
 * Аналог {@link SceneTooltip} с пробросом React-контекстов из основного дерева.
 *
 * Использует {@link BridgedHtml} вместо `Html`, чтобы Mantine-компоненты
 * и другие элементы, зависящие от провайдеров (MantineProvider),
 * работали внутри Canvas. Для тултипов без Mantine-компонентов
 * достаточно обычного {@link SceneTooltip}.
 */
export function BridgedSceneTooltip({ position, children }: PropsWithChildren<SceneTooltipProps>) {
  return (
    <BridgedHtml
      position={position}
      center
      className={styles.wrapper}
      zIndexRange={[MAP_SCENE.TOOLTIP_Y, MAP_SCENE.TOOLTIP_Y]}
    >
      <div className={styles.tooltip}>{children}</div>
    </BridgedHtml>
  );
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
