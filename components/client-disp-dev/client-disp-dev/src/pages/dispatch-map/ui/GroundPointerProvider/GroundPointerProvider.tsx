import type { PropsWithChildren, RefObject } from 'react';
import { createContext, use, useRef } from 'react';
import { Vector3 } from 'three';

/**
 * Значение контекста координат мыши на плоскости карты (Y=0).
 */
interface GroundPointerContextValue {
  /** Vector3 для Canvas-потребителей (читать в useFrame). */
  readonly pointerRef: RefObject<Vector3>;
  /** DOM ref для отображения X в StatusBar. */
  readonly xRef: RefObject<HTMLSpanElement | null>;
  /** DOM ref для отображения Y (Z сцены) в StatusBar. */
  readonly yRef: RefObject<HTMLSpanElement | null>;
}

const GroundPointerContext = createContext<GroundPointerContextValue | null>(null);

/**
 * Провайдер контекста координат мыши на плоскости карты.
 */
export function GroundPointerProvider({ children }: Readonly<PropsWithChildren>) {
  const pointerRef = useRef(new Vector3());
  const xRef = useRef<HTMLSpanElement>(null);
  const yRef = useRef<HTMLSpanElement>(null);

  const value = useRef<GroundPointerContextValue>({ pointerRef, xRef, yRef }).current;

  return <GroundPointerContext value={value}>{children}</GroundPointerContext>;
}

/**
 * Хук контекста для доступа к координатам мыши на плоскости карты (Y=0).
 */
export function useGroundPointerContext() {
  const context = use(GroundPointerContext);
  if (!context) throw new Error('useGroundPointer must be used within GroundPointerProvider');

  return context;
}
