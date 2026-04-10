import type { PropsWithChildren, RefObject } from 'react';
import { createContext, use, useRef } from 'react';
import { Vector3 } from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';

import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';

import { MAP_SCENE } from '../../config/map-scene';
import { mapActions } from '../../model/slice';

/**
 * Значение контекста камеры карты.
 */
interface MapCameraContextValue {
  /** Ref на OrbitControls для привязки к `<OrbitControls>` и блокировки панорамирования. */
  readonly controlsRef: RefObject<OrbitControlsImpl | null>;
  /** Ref на кнопку компаса для прямого обновления CSS-поворота. */
  readonly compassRef: RefObject<HTMLButtonElement | null>;
  /** Приближение камеры на один шаг. */
  readonly zoomIn: () => void;
  /** Отдаление камеры на один шаг. */
  readonly zoomOut: () => void;
  /** Сброс камеры в начальную позицию. */
  readonly resetCamera: () => void;
}

const MapCameraContext = createContext<MapCameraContextValue | null>(null);

/**
 * Провайдер контекста камеры карты.
 *
 * Управляет OrbitControls ref и предоставляет функции зума и сброса камеры.
 */
export function MapCameraProvider({ children }: Readonly<PropsWithChildren>) {
  const controlsRef = useRef<OrbitControlsImpl>(null);
  const compassRef = useRef<HTMLButtonElement>(null);
  const dispatch = useAppDispatch();

  const zoomIn = () => {
    if (controlsRef.current) zoom(controlsRef.current, MAP_SCENE.ZOOM_STEP);
  };

  const zoomOut = () => {
    if (controlsRef.current) zoom(controlsRef.current, 1 / MAP_SCENE.ZOOM_STEP);
  };

  const resetCamera = () => {
    const controls = controlsRef.current;
    if (!controls) return;

    dispatch(mapActions.clearFocusTarget());
    controls.target.set(...MAP_SCENE.CAMERA.INITIAL_TARGET);
    controls.object.position.set(...MAP_SCENE.CAMERA.INITIAL_POSITION);
    controls.update();
  };

  const value = useRef<MapCameraContextValue>({ controlsRef, compassRef, zoomIn, zoomOut, resetCamera }).current;

  return <MapCameraContext value={value}>{children}</MapCameraContext>;
}

/**
 * Масштабирует дистанцию камеры.
 *
 * @param controls инстанс OrbitControls с привязанной камерой.
 * @param factor множитель дистанции: `< 1` — приближение, `> 1` — отдаление.
 */
function zoom(controls: OrbitControlsImpl, factor: number) {
  const camera = controls.object;
  const offset = new Vector3().subVectors(camera.position, controls.target);
  const clamped = Math.max(
    MAP_SCENE.CAMERA_MIN_DISTANCE,
    Math.min(offset.length() * factor, MAP_SCENE.CAMERA_MAX_DISTANCE),
  );
  offset.setLength(clamped);
  camera.position.copy(controls.target).add(offset);
  controls.update();
}

/**
 * Хук контекста для доступа к камере карты (OrbitControls ref, зум, сброс).
 */
export function useMapCameraContext() {
  const context = use(MapCameraContext);
  if (!context) throw new Error('useMapCameraContext must be used within MapCameraProvider');

  return context;
}
