import { Html } from '@react-three/drei';
import type { HtmlProps } from '@react-three/drei/web/Html';
import { useFrame } from '@react-three/fiber';
import type { PropsWithChildren } from 'react';
import { useRef } from 'react';
import { MathUtils } from 'three';

/**
 * Представляет свойства компонента {@link ProximityHtml}.
 */
interface ProximityHtmlProps extends HtmlProps {
  /** Дистанция камеры, ближе которой элемент начинает уменьшаться. */
  readonly threshold: number;
  /** Минимальный визуальный масштаб при максимальном приближении камеры (множитель от baseScale). */
  readonly minScale: number;
  /** Базовый масштаб элемента (по умолчанию 1). Уменьшает исходный CSS-размер. */
  readonly baseScale?: number;
}

/**
 * Обёртка над drei `<Html>` с уменьшением при приближении камеры.
 *
 * Элемент отображается в фиксированном экранном размере (без `distanceFactor`).
 * Когда камера приближается ближе {@link ProximityHtmlProps.threshold},
 * масштаб плавно (smoothstep) уменьшается до {@link ProximityHtmlProps.minScale}.
 *
 * Использует орбитальную дистанцию камеры (уровень зума), а не расстояние
 * до конкретного маркера, чтобы все элементы масштабировались одинаково
 * при наклонённой (2.5D) камере.
 */
export function ProximityHtml({
  threshold,
  minScale,
  baseScale = 1,
  children,
  ...htmlProps
}: PropsWithChildren<ProximityHtmlProps>) {
  const scaleRef = useRef<HTMLDivElement>(null);

  useFrame((state) => {
    if (!scaleRef.current) return;

    const controls = state.controls as { getDistance?: () => number } | null;
    const distance = controls?.getDistance?.() ?? state.camera.position.length();
    const t = MathUtils.smoothstep(distance, 0, threshold);
    const scale = baseScale * MathUtils.lerp(minScale, 1, t);

    scaleRef.current.style.transform = `scale(${scale})`;
  });

  return (
    <Html {...htmlProps}>
      <div ref={scaleRef}>{children}</div>
    </Html>
  );
}
