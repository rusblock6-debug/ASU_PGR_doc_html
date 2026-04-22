/**
 * Компонент для отрисовки транспортного средства в 3D
 * С плавной интерполяцией движения и поворота
 */
import React, { useState, useEffect, useRef } from 'react';
import { Text, Billboard, Html } from '@react-three/drei';
import { VehiclePosition } from '../../types/graph';
import * as THREE from 'three';
import { Box } from '@react-three/drei';
import { getCachedBelazModel, isBelazModelLoaded, preloadBelazModel } from '../../utils/modelLoader';
import { useFrame } from '@react-three/fiber';

interface VehicleSphereProps {
  vehicle: VehiclePosition;
  /** При первом реальном обновлении с бэкенда — один раз телепортировать в точку, затем плавное движение */
  teleportToTarget?: boolean;
  onFirstTeleportDone?: (vehicleId: string) => void;
}

// Кеш для обработанной модели (с центрированием и масштабированием)
let processedModelCache: THREE.Object3D | null = null;

/** Если модель слишком далеко от целевой точки (накопленный лаг) — телепортируемся к цели */
const TELEPORT_DISTANCE_THRESHOLD_M = 80;
/** Минимальная скорость (м/с) при малом расстоянии до цели */
const MIN_MOVE_SPEED_MPS = 5;
/** Максимальная скорость (м/с) при большом расстоянии — догоняем быстрее */
const MAX_MOVE_SPEED_MPS = 120;
/** Коэффициент: чем дальше до цели, тем быстрее едем */
const ADAPTIVE_SPEED_FACTOR = 0.5;

/**
 * Обрабатывает модель: центрирует, масштабирует и настраивает материалы
 */
function processModel(model: THREE.Object3D): THREE.Object3D {
  try {
    const cloned = model.clone();
    
    // Вычисляем bounding box для определения размера и позиции модели
    const box = new THREE.Box3().setFromObject(cloned);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    
    // Центрируем модель: перемещаем все дочерние объекты так, чтобы центр был в (0,0,0)
    // Это важно для правильного позиционирования через group
    if (center.x !== 0 || center.y !== 0 || center.z !== 0) {
      cloned.traverse((child) => {
        if (child instanceof THREE.Mesh || child instanceof THREE.Group) {
          child.position.sub(center);
        }
      });
      // Сбрасываем позицию модели, так как мы переместили дочерние объекты
      cloned.position.set(0, 0, 0);
    }
    
    // Пересчитываем bounding box после центрирования для правильного масштабирования
    const boxAfter = new THREE.Box3().setFromObject(cloned);
    const sizeAfter = boxAfter.getSize(new THREE.Vector3());
    const centerAfter = boxAfter.getCenter(new THREE.Vector3());
    
    // Настраиваем масштаб модели
    const maxDimension = Math.max(sizeAfter.x, sizeAfter.y, sizeAfter.z);
    const targetSize = 20; // Целевой размер модели (увеличен в 2 раза)
    let appliedScale = 1.0;
    let modelHeightAfterScale = 0;
    
    if (maxDimension > 0) {
      // Всегда масштабируем модель до целевого размера для единообразия
      appliedScale = targetSize / maxDimension;
      cloned.scale.setScalar(appliedScale);
      
      // Пересчитываем размер после масштабирования для проверки
      const boxAfterScale = new THREE.Box3().setFromObject(cloned);
      const sizeAfterScale = boxAfterScale.getSize(new THREE.Vector3());
      modelHeightAfterScale = sizeAfterScale.y; // Высота модели после масштабирования
    }
    
    // Поднимаем модель вверх, чтобы колеса были на уровне земли
    if (modelHeightAfterScale > 0) {
      const yOffset = modelHeightAfterScale * 0.6; // Поднимаем на 60% высоты для правильного позиционирования колес
      cloned.position.y = yOffset;
    }
    
    // Применяем материалы, тени и единый цвет модели
    cloned.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.castShadow = true;
        child.receiveShadow = true;
        child.visible = true;

        // Общая нормализация материалов и установка цвета
        if (child.material) {
          const materials: THREE.Material[] = Array.isArray(child.material)
            ? child.material
            : [child.material];

          materials.forEach((mat: any) => {
            mat.needsUpdate = true;
            mat.visible = true;
            if ('transparent' in mat && mat.transparent && 'opacity' in mat && mat.opacity < 0.5) {
              mat.opacity = 1.0;
              mat.transparent = false;
            }
            // Задаём оранжевый цвет #E8793EFF (alpha берём из opacity материала)
            if ('color' in mat && mat.color && typeof mat.color.set === 'function') {
              mat.color.set(0xE8793E);
            }
          });
        }
      }
    });
    
    return cloned;
  } catch (error) {
    console.error('Error processing Belaz model:', error);
    throw error;
  }
}

export function VehicleSphere({ vehicle, teleportToTarget, onFirstTeleportDone }: VehicleSphereProps) {
  const [modelLoaded, setModelLoaded] = useState(false);
  const [modelError, setModelError] = useState(false);
  const [clonedModel, setClonedModel] = useState<THREE.Object3D | null>(null);
  
  // Ref для доступа к group (для камеры)
  const groupRef = useRef<THREE.Group>(null);
  
  // Состояние для плавной интерполяции
  const currentPosition = useRef(new THREE.Vector3(0, 0, 0));
  const targetPosition = useRef(new THREE.Vector3(0, 0, 0));
  const currentRotation = useRef(0);
  const targetRotation = useRef(0);
  const lastUpdateTime = useRef(Date.now());
  const speed = useRef(0);
  const initialized = useRef(false);
  
  // Храним предыдущие значения для определения изменений
  const prevVehicle = useRef<{x: number, y: number, z: number, rotation: number}>({x: 0, y: 0, z: 0, rotation: 0});
  
  // Загружаем и обрабатываем модель при монтировании
  useEffect(() => {
    // Функция для получения обработанной модели
    const getProcessedModel = (): THREE.Object3D | null => {
      // Если модель уже обработана и закеширована, используем её
      if (processedModelCache) {
        return processedModelCache;
      }
      
      // Проверяем, загружена ли модель в глобальном кеше
      const cachedModel = getCachedBelazModel();
      if (cachedModel) {
        try {
          const processed = processModel(cachedModel);
          processedModelCache = processed;
          return processed;
        } catch (error) {
          console.error('❌ Failed to process cached model:', error);
          return null;
        }
      }
      
      return null;
    };
    
    // Если модель уже обработана и закеширована, используем её сразу
    const processed = getProcessedModel();
    if (processed) {
      // Клонируем модель для этого экземпляра VehicleSphere
      setClonedModel(processed.clone());
      setModelLoaded(true);
      return;
    }
    
    // Если модель не загружена, пытаемся загрузить
    if (!isBelazModelLoaded()) {
      preloadBelazModel()
        .then((model) => {
          try {
            const processed = processModel(model);
            processedModelCache = processed;
            // Клонируем модель для этого экземпляра VehicleSphere
            setClonedModel(processed.clone());
            setModelLoaded(true);
          } catch (error) {
            console.error('❌ Failed to process preloaded model:', error);
            setModelError(true);
          }
        })
        .catch((error) => {
          console.error('❌ Failed to preload Belaz model:', error);
          setModelError(true);
        });
    } else {
      // Модель загружена, но еще не обработана - обрабатываем
      const processed = getProcessedModel();
      if (processed) {
        setClonedModel(processed.clone());
        setModelLoaded(true);
      }
    }
  }, []);
  
  // Используем Canvas координаты для 3D позиции (если есть), иначе fallback на GPS
  // В 3D сцене: X = canvasX (восток-запад), Y = height (высота), Z = -canvasY (север-юг, инвертировано)
  const targetX = vehicle.canvasX ?? vehicle.lon;
  const targetY = (vehicle.height ?? 0);  // Используем высоту как есть
  const targetZ = vehicle.canvasY !== undefined && vehicle.canvasY !== null 
    ? -vehicle.canvasY  // Инвертируем canvasY для правильной ориентации в 3D
    : -vehicle.lat;
  
  // Используем угол поворота из vehicle (вычисляется в ThreeView на основе движения)
  const targetRot = vehicle.rotation ?? 0;
  
  // Обновляем целевую позицию при изменении данных машины
  useEffect(() => {
    const newTarget = new THREE.Vector3(targetX, targetY, targetZ);
    
    // Проверяем изменилась ли позиция
    if (!targetPosition.current.equals(newTarget)) {
      // Вычисляем скорость на основе расстояния и времени
      const now = Date.now();
      const timeDelta = (now - lastUpdateTime.current) / 1000; // секунды
      
      if (timeDelta > 0 && initialized.current) {
        const distance = targetPosition.current.distanceTo(newTarget);
        speed.current = distance / timeDelta; // м/с
      }
      
      // Если первая инициализация - телепортируем, иначе плавно двигаем
      if (!initialized.current) {
        currentPosition.current.copy(newTarget);
        targetPosition.current.copy(newTarget);
        currentRotation.current = targetRot;
        targetRotation.current = targetRot;
        initialized.current = true;
        
        // Устанавливаем начальную позицию группы СРАЗУ
        if (groupRef.current) {
          groupRef.current.position.copy(newTarget);
          groupRef.current.rotation.y = targetRot;
        }
      } else {
        // НЕ сбрасываем currentPosition - просто обновляем цель
        // Машинка плавно доедет до новой цели от текущей позиции
        targetPosition.current.copy(newTarget);
      }
      
      lastUpdateTime.current = now;
    }
    
    // Обновляем целевой угол поворота (только если изменился значительно)
    const rotDiff = targetRot - targetRotation.current;
    const normalizedDiff = Math.atan2(Math.sin(rotDiff), Math.cos(rotDiff)); // Нормализуем в [-π, π]
    
    if (Math.abs(normalizedDiff) > 0.01) {
      // Просто обновляем целевой угол (не накапливаем!)
      targetRotation.current = targetRot;
    }
  }, [targetX, targetY, targetZ, targetRot]);

  // При первом реальном обновлении с WebSocket — телепорт в точку (без плавного переезда от гаража)
  useEffect(() => {
    if (!teleportToTarget || !groupRef.current) return;
    currentPosition.current.copy(targetPosition.current);
    groupRef.current.position.copy(currentPosition.current);
    currentRotation.current = targetRotation.current;
    groupRef.current.rotation.y = currentRotation.current;
    onFirstTeleportDone?.(vehicle.vehicle_id);
  }, [teleportToTarget, vehicle.vehicle_id, onFirstTeleportDone]);

  // Плавная интерполяция позиции и поворота каждый кадр. Телепорт только при накопленном лаге (модель далеко от цели).
  useFrame((state, delta) => {
    if (!groupRef.current || !initialized.current) return;
    
    // Интерполяция позиции по скорости
    const distanceToTarget = currentPosition.current.distanceTo(targetPosition.current);
    
    if (distanceToTarget > 0.01) {
      // Телепорт только когда модель слишком далеко от целевой точки (накопленный лаг) — так лаг не копится
      if (distanceToTarget > TELEPORT_DISTANCE_THRESHOLD_M) {
        currentPosition.current.copy(targetPosition.current);
        currentRotation.current = targetRotation.current;
        groupRef.current.position.copy(currentPosition.current);
        groupRef.current.rotation.y = currentRotation.current;
        return;
      }

      // Адаптивная скорость: чем дальше до цели, тем быстрее едем (догоняем, лаг не копится)
      const adaptiveSpeed = Math.min(
        MAX_MOVE_SPEED_MPS,
        MIN_MOVE_SPEED_MPS + distanceToTarget * ADAPTIVE_SPEED_FACTOR
      );
      const moveSpeed = Math.max(speed.current, adaptiveSpeed);
      const moveDistance = moveSpeed * delta;
      const progress = Math.min(moveDistance / distanceToTarget, 1.0);
      
      // Двигаем текущую позицию к целевой
      currentPosition.current.lerp(targetPosition.current, progress);
      
      // Обновляем позицию group
      groupRef.current.position.copy(currentPosition.current);
    }
    
    // Плавная интерполяция поворота
    const rotationDiff = Math.abs(currentRotation.current - targetRotation.current);
    
    if (rotationDiff > 0.01) {
      // Плавный поворот (10% каждый кадр, но не медленнее чем 2 рад/с)
      const rotationSpeed = Math.max(delta * 2, 0.1); // Минимум 0.1 (10% за кадр)
      
      // Нормализуем разницу углов
      let diff = targetRotation.current - currentRotation.current;
      if (diff > Math.PI) diff -= 2 * Math.PI;
      if (diff < -Math.PI) diff += 2 * Math.PI;
      
      currentRotation.current += diff * rotationSpeed;
      
      // Нормализуем текущий угол в диапазоне [0, 2π]
      currentRotation.current = ((currentRotation.current % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
      
      // Обновляем поворот group
      groupRef.current.rotation.y = currentRotation.current;
    }
  });
  
  // Логируем координаты для отладки
  // Визуальный маркер для отладки позиции (красная сфера в позиции машины)
  const showDebugMarker = false; // Отключено для production
  
  // Смещение модели уже применено внутри processedModel (cloned.position.y)
  // Не нужно добавлять дополнительное смещение в group position
  
  return (
    <group ref={groupRef} name={`vehicle-${vehicle.vehicle_id}`}>
      {/* Визуальный маркер для отладки - показывает где должна быть машина */}
      {showDebugMarker && (
        <>
          <mesh position={[0, 0, 0]}>
            <sphereGeometry args={[5, 16, 16]} />
            <meshBasicMaterial color="#ff0000" transparent opacity={0.7} />
          </mesh>
          {/* Дополнительный маркер - большой куб для проверки видимости */}
          <mesh position={[0, 5, 0]}>
            <boxGeometry args={[10, 10, 10]} />
            <meshBasicMaterial color="#00ff00" transparent opacity={0.5} />
          </mesh>
        </>
      )}
      
      {/* Рендерим модель: сначала красная fallback, потом Белаз когда загрузится */}
      {modelLoaded && clonedModel ? (
        // Показываем Белаз когда загружен
        <primitive object={clonedModel} />
      ) : (
        // Показываем красную модельку пока загружается Белаз или при ошибке
        <>
          {/* Тёмно-красный самосвал: кабина СПЕРЕДИ (вдоль направления движения +X) */}
          
          {/* Кабина (передняя часть) - вдоль направления движения +X */}
          <Box args={[4, 3.5, 6]} position={[6, 0, 0]}>
            <meshBasicMaterial color="#8B0000" />  {/* Тёмно-красный DarkRed */}
          </Box>
          
          {/* Кузов (задняя часть БЕЗ наклона) */}
          <Box args={[8, 3, 6]} position={[0, 0, 0]}>
            <meshBasicMaterial color="#A52A2A" />  {/* Коричнево-красный Brown */}
          </Box>
          
          {/* Колёса (4 шт) - БОЛЬШИЕ цилиндры, ось вдоль кабины (Z) */}
          <mesh position={[5, -2.5, 3]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[1.5, 1.5, 1.2, 8]} />  {/* Увеличены: радиус 1.5, ширина 1.2 */}
            <meshBasicMaterial color="#222222" />
          </mesh>
          <mesh position={[5, -2.5, -3]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[1.5, 1.5, 1.2, 8]} />
            <meshBasicMaterial color="#222222" />
          </mesh>
          <mesh position={[-1, -2.5, 3]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[1.5, 1.5, 1.2, 8]} />
            <meshBasicMaterial color="#222222" />
          </mesh>
          <mesh position={[-1, -2.5, -3]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[1.5, 1.5, 1.2, 8]} />
            <meshBasicMaterial color="#222222" />
          </mesh>
        </>
      )}
      
      <Billboard
        position={[0, 20, 0]}
        follow={true}
        lockX={false}
        lockY={false}
        lockZ={false}
        renderOrder={100}
      >
        <Text
          fontSize={4}
          color="#FFFFFF"
          anchorX="center"
          anchorY="middle"
          position={[0, 0, 0]}
          outlineWidth={0.5}
          outlineColor="#000000"
        >
          {vehicle.name || vehicle.vehicle_id}
        </Text>
      </Billboard>

      {/* Значок загрузки/разгрузки/движения с грузом над машиной при loading/unloading/moving_loaded */}
      {(vehicle.state === 'loading' || vehicle.state === 'unloading' || vehicle.state === 'moving_loaded') && (
        <Billboard
          position={[0, 30, 0]}
          follow={true}
          lockX={false}
          lockY={false}
          lockZ={false}
          renderOrder={100}
        >
          <Text
            fontSize={5}
            color={
              vehicle.state === 'loading' 
                ? '#FFD700'  // Желтый для погрузки
                : vehicle.state === 'moving_loaded'
                ? '#00FF00'  // Зеленый для движения с грузом
                : '#FFA500'  // Оранжевый для разгрузки
            }
            anchorX="center"
            anchorY="middle"
            position={[0, 0, 0]}
            outlineWidth={0.3}
            outlineColor="#000000"
            >
              📦
          </Text>
        </Billboard>
      )}

      {/* Значки сна (Z) над машиной при stopped_empty - несколько штук, исходящих от машины */}
      {vehicle.state === 'stopped_empty' && (
        <>
          <Billboard
            position={[-2, 30, 0]}
            follow={true}
            lockX={false}
            lockY={false}
            lockZ={false}
            renderOrder={100}
          >
            <Text
              fontSize={6}
              color="#87CEEB"
              anchorX="center"
              anchorY="middle"
              position={[0, 0, 0]}
              outlineWidth={0.3}
              outlineColor="#000000"
            >
              Z
            </Text>
          </Billboard>
          <Billboard
            position={[0, 36, 0]}
            follow={true}
            lockX={false}
            lockY={false}
            lockZ={false}
            renderOrder={100}
          >
            <Text
              fontSize={7}
              color="#87CEEB"
              anchorX="center"
              anchorY="middle"
              position={[0, 0, 0]}
              outlineWidth={0.3}
              outlineColor="#000000"
            >
              Z
            </Text>
          </Billboard>
          <Billboard
            position={[2, 30, 0]}
            follow={true}
            lockX={false}
            lockY={false}
            lockZ={false}
            renderOrder={100}
          >
            <Text
              fontSize={6}
              color="#87CEEB"
              anchorX="center"
              anchorY="middle"
              position={[0, 0, 0]}
              outlineWidth={0.3}
              outlineColor="#000000"
            >
              Z
            </Text>
          </Billboard>
        </>
      )}

    </group>
  );
}



