/**
 * Утилита для предзагрузки и кеширования 3D моделей
 * Использует двухуровневое кеширование:
 * 1. Memory cache - для быстрого доступа в рамках сессии
 * 2. IndexedDB cache - для персистентного хранения между сессиями
 */
import { FBXLoader } from 'three/examples/jsm/loaders/FBXLoader.js';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import * as THREE from 'three';
import { getCachedModel, cacheModel } from './modelCache';

/**
 * Нормализует материалы модели, заменяя неизвестные типы на стандартные
 */
function normalizeMaterials(object: THREE.Object3D): void {
  object.traverse((child) => {
    if (child instanceof THREE.Mesh && child.material) {
      const materials = Array.isArray(child.material) ? child.material : [child.material];
      
      materials.forEach((material, index) => {
        // Если материал имеет неизвестный тип или не является стандартным материалом Three.js
        if (!material || material.type === 'unknown' || !(material instanceof THREE.Material)) {
          // Создаем стандартный материал на основе существующего, если возможно
          const newMaterial = new THREE.MeshPhongMaterial({
            color: (material as any)?.color || 0xffffff,
            map: (material as any)?.map || null,
            normalMap: (material as any)?.normalMap || null,
          });
          
          if (Array.isArray(child.material)) {
            child.material[index] = newMaterial;
          } else {
            child.material = newMaterial;
          }
        }
      });
    }
  });
}

// Глобальный кеш для загруженной модели
let cachedBelazModel: THREE.Object3D | null = null;
let loadingPromise: Promise<THREE.Object3D> | null = null;
let isLoading = false;

// Глобальный кеш для модели экскаватора
let cachedExcavatorModel: THREE.Object3D | null = null;
let excavatorLoadingPromise: Promise<THREE.Object3D> | null = null;
let isExcavatorLoading = false;

/**
 * Тип для callback функции прогресса загрузки
 */
export type ProgressCallback = (loaded: number, total: number) => void;

/**
 * Загружает FBX модель из URL с поддержкой кеширования
 * @param url URL модели
 * @param onProgress Callback для отслеживания прогресса загрузки
 * @returns Promise с ArrayBuffer содержащим данные модели
 */
async function loadModelData(url: string, onProgress?: ProgressCallback): Promise<ArrayBuffer> {
  // Проверяем IndexedDB кеш
  const cachedData = await getCachedModel(url);
  if (cachedData) {
    if (onProgress) {
      onProgress(cachedData.byteLength, cachedData.byteLength);
    }
    return cachedData;
  }

  // Загружаем с сервера
  const startTime = performance.now();
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load model: ${response.statusText}`);
  }

  const contentLength = response.headers.get('content-length');
  const total = contentLength ? parseInt(contentLength, 10) : 0;

  // Читаем данные по частям с отслеживанием прогресса
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Failed to get response reader');
  }

  const chunks: Uint8Array[] = [];
  let loaded = 0;

  while (true) {
    const { done, value } = await reader.read();
    
    if (done) break;
    
    chunks.push(value);
    loaded += value.length;
    
    // Вызываем callback прогресса
    if (onProgress && total > 0) {
      onProgress(loaded, total);
    }
  }

  // Объединяем все чанки в один ArrayBuffer
  const arrayBuffer = new Uint8Array(loaded);
  let offset = 0;
  for (const chunk of chunks) {
    arrayBuffer.set(chunk, offset);
    offset += chunk.length;
  }

  const loadTime = (performance.now() - startTime).toFixed(0);
  console.log(`✅ [Model Loader] Загружено за ${loadTime}мс`);

  // 3. Сохраняем в IndexedDB кеш (асинхронно, не блокируем)
  cacheModel(url, arrayBuffer.buffer).catch((error) => {
    console.warn('⚠️ [Model Loader] Не удалось сохранить модель в кеш:', error);
  });

  return arrayBuffer.buffer;
}

/**
 * Предзагружает FBX модель трака и кеширует её
 * @param onProgress Callback для отслеживания прогресса загрузки
 * @returns Promise с загруженной моделью
 */
export async function preloadBelazModel(onProgress?: ProgressCallback): Promise<THREE.Object3D> {
  // Если модель уже загружена в память, возвращаем её
  if (cachedBelazModel) {
    return cachedBelazModel;
  }

  // Если уже идет загрузка, возвращаем существующий промис
  if (loadingPromise) {
    return loadingPromise;
  }

  // Начинаем загрузку
  isLoading = true;
  
  loadingPromise = (async () => {
    try {
      // Ранее здесь грузилась FBX-модель belaz.FBX.
      // Теперь используем STL-модель UGTruck_Svk.stl (она не содержит материалов, материал создаём явно).
      const modelUrl = '/static/3dm/has/UGTruck_Svk.stl';
      
      // Загружаем данные модели (с кешированием и прогрессом)
      const arrayBuffer = await loadModelData(modelUrl, onProgress);
      
      // Парсим STL из ArrayBuffer
      // STLLoader.parse() синхронно возвращает BufferGeometry
      const loader = new STLLoader();
      const geometry = loader.parse(arrayBuffer);
      // Задаём единый цвет модели (оранжевый #E8793E)
      const material = new THREE.MeshPhongMaterial({
        color: 0xE8793E,
      });
      const mesh = new THREE.Mesh(geometry, material);
      // Для обратной совместимости возвращаем Object3D (Group), как и раньше для FBX
      const object = new THREE.Group();
      object.add(mesh);

      // Нормализуем материалы для устранения предупреждений о неизвестных типах
      normalizeMaterials(object);
      
      cachedBelazModel = object;
      isLoading = false;
      return object;
    } catch (error) {
      console.error('❌ [Model Loader] Failed to preload Belaz model:', error);
      isLoading = false;
      loadingPromise = null;
      throw error;
    }
  })();

  return loadingPromise;
}

/**
 * Получает закешированную модель трака
 * @returns Загруженная модель или null, если модель еще не загружена
 */
export function getCachedBelazModel(): THREE.Object3D | null {
  return cachedBelazModel;
}

/**
 * Проверяет, загружена ли модель
 */
export function isBelazModelLoaded(): boolean {
  return cachedBelazModel !== null;
}

/**
 * Проверяет, идет ли загрузка модели
 */
export function isBelazModelLoading(): boolean {
  return isLoading;
}

/**
 * Предзагружает FBX модель экскаватора и кеширует её
 * @param onProgress Callback для отслеживания прогресса загрузки
 * @returns Promise с загруженной моделью
 */
export async function preloadExcavatorModel(onProgress?: ProgressCallback): Promise<THREE.Object3D> {
  // Если модель уже загружена в память, возвращаем её
  if (cachedExcavatorModel) {
    return cachedExcavatorModel;
  }

  // Если уже идет загрузка, возвращаем существующий промис
  if (excavatorLoadingPromise) {
    return excavatorLoadingPromise;
  }

  // Начинаем загрузку
  isExcavatorLoading = true;
  
  excavatorLoadingPromise = (async () => {
    try {
      // Пробуем загрузить файл с разными возможными именами
      // Примечание: имя файла с заглавной кириллической буквой Е
      const possibleNames = [
        '/static/3dm/shovel/екскаватор.FBX',
        '/static/3dm/shovel/Екскаватор.FBX',
        '/static/3dm/shovel/ЕКСКАВАТОР.FBX',
        '/static/3dm/shovel/excavator.FBX',
        '/static/3dm/shovel/shovel.FBX',
        '/static/3dm/shovel/екскалатор.FBX'
      ];
      
      let arrayBuffer: ArrayBuffer | null = null;
      let successUrl: string | null = null;
      
      // Пробуем загрузить первый доступный файл
      for (const url of possibleNames) {
        try {
          arrayBuffer = await loadModelData(url, onProgress);
          successUrl = url;
          break;
        } catch (error) {
          // Пробуем следующий вариант
          continue;
        }
      }
      
      if (!arrayBuffer || !successUrl) {
        throw new Error('No valid excavator model file found');
      }
      
      // Парсим FBX из ArrayBuffer
      // FBXLoader.parse() синхронно возвращает результат, не использует callbacks
      const loader = new FBXLoader();
      const object = loader.parse(arrayBuffer, '');

      // Нормализуем материалы для устранения предупреждений о неизвестных типах
      normalizeMaterials(object);
      
      cachedExcavatorModel = object;
      isExcavatorLoading = false;
      excavatorLoadingPromise = null;
      return object;
    } catch (error) {
      console.error('❌ [Model Loader] Failed to load excavator model:', error);
      isExcavatorLoading = false;
      excavatorLoadingPromise = null;
      throw error;
    }
  })();

  return excavatorLoadingPromise;
}

/**
 * Получает закешированную модель экскаватора
 * @returns Загруженная модель или null, если модель еще не загружена
 */
export function getCachedExcavatorModel(): THREE.Object3D | null {
  return cachedExcavatorModel;
}

/**
 * Проверяет, загружена ли модель экскаватора
 */
export function isExcavatorModelLoaded(): boolean {
  return cachedExcavatorModel !== null;
}

/**
 * Проверяет, идет ли загрузка модели экскаватора
 */
export function isExcavatorModelLoading(): boolean {
  return isExcavatorLoading;
}

