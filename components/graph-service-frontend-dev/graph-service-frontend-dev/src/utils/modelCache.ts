/**
 * Утилита для кеширования 3D моделей в IndexedDB браузера
 * Позволяет избежать повторной загрузки моделей при перезагрузке страницы
 */

interface CachedModel {
  url: string;
  data: ArrayBuffer;
  timestamp: number;
  version: string;
}

const DB_NAME = 'ThreeJSModelCache';
const DB_VERSION = 1;
const STORE_NAME = 'models';
const CACHE_VERSION = '1.0'; // Увеличивайте при изменении формата моделей
const CACHE_EXPIRY_DAYS = 7; // Модели устаревают через 7 дней

/**
 * Инициализирует IndexedDB базу данных
 */
async function initDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      
      // Создаем хранилище для моделей если его еще нет
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const objectStore = db.createObjectStore(STORE_NAME, { keyPath: 'url' });
        objectStore.createIndex('timestamp', 'timestamp', { unique: false });
        console.log('📦 [Model Cache] IndexedDB initialized');
      }
    };
  });
}

/**
 * Проверяет, устарела ли закешированная модель
 */
function isCacheExpired(timestamp: number): boolean {
  const now = Date.now();
  const expiryTime = CACHE_EXPIRY_DAYS * 24 * 60 * 60 * 1000;
  return now - timestamp > expiryTime;
}

/**
 * Сохраняет модель в IndexedDB кеш
 */
export async function cacheModel(url: string, data: ArrayBuffer): Promise<void> {
  try {
    const db = await initDB();
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);

    const cachedModel: CachedModel = {
      url,
      data,
      timestamp: Date.now(),
      version: CACHE_VERSION,
    };

    await new Promise<void>((resolve, reject) => {
      const request = store.put(cachedModel);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });

    db.close();
  } catch (error) {
    console.error('❌ [Model Cache] Ошибка сохранения в кеш:', error);
  }
}

/**
 * Загружает модель из IndexedDB кеша
 */
export async function getCachedModel(url: string): Promise<ArrayBuffer | null> {
  try {
    const db = await initDB();
    const transaction = db.transaction([STORE_NAME], 'readonly');
    const store = transaction.objectStore(STORE_NAME);

    const cachedModel = await new Promise<CachedModel | null>((resolve, reject) => {
      const request = store.get(url);
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error);
    });

    db.close();

    if (!cachedModel) {
      return null;
    }

    // Проверяем версию кеша
    if (cachedModel.version !== CACHE_VERSION) {
      await deleteCachedModel(url);
      return null;
    }

    // Проверяем срок годности
    if (isCacheExpired(cachedModel.timestamp)) {
      await deleteCachedModel(url);
      return null;
    }

    return cachedModel.data;
  } catch (error) {
    console.error('❌ [Model Cache] Ошибка загрузки из кеша:', error);
    return null;
  }
}

/**
 * Удаляет модель из кеша
 */
export async function deleteCachedModel(url: string): Promise<void> {
  try {
    const db = await initDB();
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);

    await new Promise<void>((resolve, reject) => {
      const request = store.delete(url);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });

    db.close();
  } catch (error) {
    console.error('❌ [Model Cache] Ошибка удаления из кеша:', error);
  }
}

/**
 * Очищает весь кеш моделей
 */
export async function clearModelCache(): Promise<void> {
  try {
    const db = await initDB();
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);

    await new Promise<void>((resolve, reject) => {
      const request = store.clear();
      request.onsuccess = () => {
        console.log('✅ [Model Cache] Кеш полностью очищен');
        resolve();
      };
      request.onerror = () => reject(request.error);
    });

    db.close();
  } catch (error) {
    console.error('❌ [Model Cache] Ошибка очистки кеша:', error);
  }
}

/**
 * Получает размер кеша в байтах
 */
export async function getCacheSize(): Promise<number> {
  try {
    const db = await initDB();
    const transaction = db.transaction([STORE_NAME], 'readonly');
    const store = transaction.objectStore(STORE_NAME);

    const models = await new Promise<CachedModel[]>((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });

    db.close();

    const totalSize = models.reduce((sum, model) => sum + model.data.byteLength, 0);
    return totalSize;
  } catch (error) {
    console.error('❌ [Model Cache] Ошибка получения размера кеша:', error);
    return 0;
  }
}

/**
 * Получает список всех закешированных моделей
 */
export async function listCachedModels(): Promise<{ url: string; size: number; age: number }[]> {
  try {
    const db = await initDB();
    const transaction = db.transaction([STORE_NAME], 'readonly');
    const store = transaction.objectStore(STORE_NAME);

    const models = await new Promise<CachedModel[]>((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });

    db.close();

    const now = Date.now();
    return models.map((model) => ({
      url: model.url,
      size: model.data.byteLength,
      age: Math.floor((now - model.timestamp) / 1000 / 60 / 60 / 24), // дни
    }));
  } catch (error) {
    console.error('❌ [Model Cache] Ошибка получения списка моделей:', error);
    return [];
  }
}

