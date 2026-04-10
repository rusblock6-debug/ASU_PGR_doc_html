/**
 * Хук для централизованной загрузки и кэширования данных о машинах
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { getVehicles, EnterpriseVehicle } from '../services/api';

interface UseVehiclesResult {
  vehicles: EnterpriseVehicle[];
  vehiclesMap: Map<string, EnterpriseVehicle>;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

// Глобальный кэш для предотвращения дублирования запросов
let globalVehiclesCache: EnterpriseVehicle[] | null = null;
let globalVehiclesPromise: Promise<EnterpriseVehicle[]> | null = null;

/**
 * Хук для получения списка машин из enterprise-service
 * Использует глобальный кэш для предотвращения дублирования запросов
 */
export function useVehicles(enterpriseId: number = 1): UseVehiclesResult {
  const [vehicles, setVehicles] = useState<EnterpriseVehicle[]>(globalVehiclesCache || []);
  const [loading, setLoading] = useState(!globalVehiclesCache);
  const [error, setError] = useState<string | null>(null);
  const [vehiclesMap, setVehiclesMap] = useState<Map<string, EnterpriseVehicle>>(new Map());

  const fetchVehicles = useCallback(async () => {
    // Если уже есть активный запрос, ждём его
    if (globalVehiclesPromise) {
      try {
        const result = await globalVehiclesPromise;
        setVehicles(result);
        setLoading(false);
        return;
      } catch (err) {
        // Продолжаем к новому запросу
      }
    }

    // Если есть кэш, используем его
    if (globalVehiclesCache) {
      setVehicles(globalVehiclesCache);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Создаём Promise и сохраняем глобально
      globalVehiclesPromise = getVehicles(enterpriseId);
      const result = await globalVehiclesPromise;
      
      globalVehiclesCache = result;
      setVehicles(result);
      
      console.log(`✅ [useVehicles] Загружено ${result.length} машин`);
    } catch (err) {
      console.error('❌ [useVehicles] Ошибка загрузки машин:', err);
      setError('Не удалось загрузить список машин');
    } finally {
      setLoading(false);
      globalVehiclesPromise = null;
    }
  }, [enterpriseId]);

  // Принудительная перезагрузка (сбрасывает кэш)
  const refetch = useCallback(async () => {
    globalVehiclesCache = null;
    globalVehiclesPromise = null;
    await fetchVehicles();
  }, [fetchVehicles]);

  // Загружаем при монтировании
  useEffect(() => {
    fetchVehicles();
  }, [fetchVehicles]);

  // Создаём Map для быстрого поиска по id
  useEffect(() => {
    const map = new Map<string, EnterpriseVehicle>();
    vehicles.forEach(vehicle => {
      // Используем id как ключ (конвертируем в строку)
      map.set(String(vehicle.id), vehicle);
    });
    setVehiclesMap(map);
  }, [vehicles]);

  return {
    vehicles,
    vehiclesMap,
    loading,
    error,
    refetch
  };
}

/**
 * Получить ключ машины (vehicle_id) из объекта EnterpriseVehicle
 */
export function getVehicleKey(vehicle: EnterpriseVehicle): string {
  return String(vehicle.id);
}

/**
 * Сбросить глобальный кэш машин (например при logout)
 */
export function clearVehiclesCache(): void {
  globalVehiclesCache = null;
  globalVehiclesPromise = null;
}

export default useVehicles;



