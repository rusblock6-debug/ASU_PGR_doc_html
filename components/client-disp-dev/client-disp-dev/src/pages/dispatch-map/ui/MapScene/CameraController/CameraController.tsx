import { useFrame } from '@react-three/fiber';
import { useEffect, useRef } from 'react';
import { MathUtils, Vector3 } from 'three';

import { useGetAllPlacesQuery } from '@/shared/api/endpoints/places';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { MAP_SCENE } from '../../../config/map-scene';
import { selectMapFocusTarget } from '../../../model/selectors';
import { mapActions } from '../../../model/slice';
import { useMapCameraContext } from '../../MapCameraProvider';
import type { VehicleData } from '../VehiclesLayer';

import { resolveTargetPosition } from './helpers';

/** Свойства контроллера камеры. */
interface CameraControllerProps {
  /** Текущие данные техники для фокуса по id транспорта. */
  readonly vehicles?: Record<string, VehicleData>;
}

/** Состояние анимации перелёта камеры. */
interface AnimationState {
  /** Позиция камеры в момент старта анимации. */
  readonly startCameraPos: Vector3;
  /** Точка фокуса в момент старта анимации. */
  readonly startTarget: Vector3;
  /** Смещение камеры от точки фокуса в момент старта анимации. */
  readonly startOffset: Vector3;
  /** Прогресс анимации в диапазоне [0..1]. */
  progress: number;
}

/** Переиспользуемый вектор целевой позиции для кадра. */
const targetVec = new Vector3();
/** Смещение камеры относительно точки фокуса после завершения анимации. */
const cameraOffset = new Vector3();

/**
 * Управляет камерой при фокусировке на объекте.
 * Анимирует перелёт к цели, затем удерживает камеру на объекте.
 */
export function CameraController({ vehicles }: CameraControllerProps) {
  const { controlsRef } = useMapCameraContext();
  const dispatch = useAppDispatch();
  const focusTarget = useAppSelector(selectMapFocusTarget);
  const { data: placesData } = useGetAllPlacesQuery();

  const animationRef = useRef<AnimationState | null>(null);

  useEffect(() => {
    if (!focusTarget) {
      animationRef.current = null;
      return;
    }

    const controls = controlsRef.current;
    if (!controls) return;

    animationRef.current = {
      startCameraPos: controls.object.position.clone(),
      startTarget: controls.target.clone(),
      startOffset: controls.object.position.clone().sub(controls.target),
      progress: 0,
    };
  }, [focusTarget, controlsRef]);

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls || !focusTarget) return;

    const { domElement } = controls;
    if (!domElement) return;

    const handlePointerDown = (event: PointerEvent) => {
      if (event.button === 0 && !event.ctrlKey) {
        dispatch(mapActions.clearFocusTarget());
      }
    };

    domElement.addEventListener('pointerdown', handlePointerDown);
    return () => domElement.removeEventListener('pointerdown', handlePointerDown);
  }, [controlsRef, focusTarget, dispatch]);

  useFrame((state, delta) => {
    const animation = animationRef.current;
    if (!focusTarget || !animation) return;

    const controls = controlsRef.current;
    if (!controls) return;

    const pos = resolveTargetPosition(focusTarget, vehicles, placesData?.items);
    if (!pos) return;

    const [tx, , tz] = pos;

    if (animation.progress < 1) {
      animation.progress = Math.min(1, animation.progress + delta / MAP_SCENE.CAMERA_FOCUS_DURATION);
      const easedProgress = MathUtils.smootherstep(animation.progress, 0, 1);

      targetVec.set(tx, 0, tz);
      controls.target.lerpVectors(animation.startTarget, targetVec, easedProgress);

      targetVec.set(tx, 0, tz).add(animation.startOffset);
      state.camera.position.lerpVectors(animation.startCameraPos, targetVec, easedProgress);

      controls.update();
      return;
    }

    cameraOffset.subVectors(state.camera.position, controls.target);
    controls.target.set(tx, 0, tz);
    state.camera.position.copy(controls.target).add(cameraOffset);

    controls.update();
  });

  return null;
}
