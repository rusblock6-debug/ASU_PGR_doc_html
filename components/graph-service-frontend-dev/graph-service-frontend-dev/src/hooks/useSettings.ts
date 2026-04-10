/**
 * Хук для работы с настройками приложения из localStorage
 */
import { useState, useCallback, useMemo } from 'react';

export interface OriginPoint {
  // GPS координаты опорной точки
  gpsLat: number;
  gpsLon: number;
  // Canvas координаты опорной точки
  canvasX: number;
  canvasY: number;
  canvasZ: number;
}

export interface CoordinateCalibration {
  enabled: boolean;
  origin: OriginPoint | null;
}

export interface Settings {
  coordinateCalibration: CoordinateCalibration;
  selectedVehicles: string[];  // Список bort_id (vehicle_id) выбранных машин для отслеживания
}

// УДАЛЕНО: DEFAULT_VEHICLE_HEIGHT константа
// Frontend НЕ должен иметь свою константу высоты, так как это дублирование настройки backend
// Вместо этого используется высота выбранного уровня или undefined (backend сам применит свой DEFAULT_VEHICLE_HEIGHT)

export function useSettings() {
  // Калибровка координат по опорной точке (по умолчанию ВКЛЮЧЕНА!)
  // Origin Point - РЕАЛЬНЫЙ центр графа вычислен из актуальных данных БД
  // ВЕРСИЯ 4: КАЛИБРОВКА ВКЛЮЧЕНА - узлы хранятся в GPS, нужна трансформация для Canvas!
const defaultCalibration: CoordinateCalibration = {
  enabled: true,   // ✅ ВКЛЮЧЕНО - узлы в БД хранятся в GPS координатах, нужна трансформация!
  origin: {
    gpsLat: 58.173161,   // Широта центра графа (реальный центр из БД)
    gpsLon: 59.818738,   // Долгота центра графа (реальный центр из БД)
    canvasX: 0,          // Canvas координаты центра графа
    canvasY: 0,          // Canvas координаты центра графа
    canvasZ: 0           // Высота центра графа (основной уровень = 0м, не -25м!)
  }
};
  
  const [coordinateCalibration, setCoordinateCalibration] = useState<CoordinateCalibration>(
    JSON.parse(localStorage.getItem('coordinateCalibration') || JSON.stringify(defaultCalibration))
  );

  // Выбранные машины для отслеживания (по умолчанию пустой список - показываем все)
  const [selectedVehicles, setSelectedVehiclesState] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem('selectedVehicles');
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (error) {
      // Игнорируем ошибки парсинга
    }
    return [];
  });

  // Обертка для setSelectedVehicles, которая также сохраняет в localStorage
  const setSelectedVehicles = useCallback((vehicles: string[]) => {
    localStorage.setItem('selectedVehicles', JSON.stringify(vehicles));
    setSelectedVehiclesState(vehicles);
  }, []);

  const saveSettings = useCallback((settings: Partial<Settings>) => {
    if (settings.coordinateCalibration !== undefined) {
      localStorage.setItem('coordinateCalibration', JSON.stringify(settings.coordinateCalibration));
      setCoordinateCalibration(settings.coordinateCalibration);
    }
    if (settings.selectedVehicles !== undefined) {
      // Используем setSelectedVehicles, который уже сохраняет в localStorage
      setSelectedVehicles(settings.selectedVehicles);
    }
  }, [setSelectedVehicles]);
  
  // Функция трансформации GPS координат в Canvas координаты (метрическая проекция)
  const transformGPStoCanvas = useCallback((lat: number, lon: number): {x: number, y: number} => {
    // Если калибровка выключена или не настроена, используем автоматическое масштабирование
    if (!coordinateCalibration.enabled || !coordinateCalibration.origin) {
      // ✅ Автоматическое масштабирование: умножаем на 100000 для видимости на canvas
      const SCALE = 100000;
      // ⚠️ ИНВЕРТИРУЕМ Y: в Canvas Y растёт вниз, в GPS Y (широта) растёт вверх
      return { x: lon * SCALE, y: -lat * SCALE };
    }
    
    const origin = coordinateCalibration.origin;
    
    // Константы для конверсии градусов в метры
    const METERS_PER_DEGREE_LAT = 111_320; // метров на градус широты (константа)
    
    // Метров на градус долготы зависит от широты
    const originLatRad = (origin.gpsLat * Math.PI) / 180; // радианы
    const metersPerDegreeLon = METERS_PER_DEGREE_LAT * Math.cos(originLatRad);
    
    // Разница в градусах от опорной точки
    const deltaLat = lat - origin.gpsLat;
    const deltaLon = lon - origin.gpsLon;
    
    // Конверсия в метры и добавление к canvas координатам опорной точки
    const x = origin.canvasX + (deltaLon * metersPerDegreeLon);
    // ⚠️ ИНВЕРТИРУЕМ Y: в Canvas Y растёт вниз, в GPS Y (широта) растёт вверх
    const y = origin.canvasY - (deltaLat * METERS_PER_DEGREE_LAT);
    
    return { x, y };
  }, [coordinateCalibration]);

  // ✅ Обратная функция: Canvas координаты → GPS координаты
  const transformCanvasToGPS = useCallback((x: number, y: number): {lat: number, lon: number} => {
    // Если калибровка выключена или не настроена, используем обратное масштабирование
    if (!coordinateCalibration.enabled || !coordinateCalibration.origin) {
      // ✅ Обратное масштабирование: делим на 100000
      const SCALE = 100000;
      // ⚠️ ИНВЕРТИРУЕМ Y обратно: восстанавливаем положительную широту
      return { lat: -y / SCALE, lon: x / SCALE };
    }
    
    const origin = coordinateCalibration.origin;
    
    // Константы для конверсии градусов в метры
    const METERS_PER_DEGREE_LAT = 111_320;
    const originLatRad = (origin.gpsLat * Math.PI) / 180;
    const metersPerDegreeLon = METERS_PER_DEGREE_LAT * Math.cos(originLatRad);
    
    // Разница в метрах от опорной точки
    const deltaMetersX = x - origin.canvasX;
    const deltaMetersY = y - origin.canvasY;
    
    // Конверсия обратно в градусы
    const deltaLon = deltaMetersX / metersPerDegreeLon;
    // ⚠️ ИНВЕРТИРУЕМ Y обратно: восстанавливаем положительную широту
    const deltaLat = -deltaMetersY / METERS_PER_DEGREE_LAT;
    
    return {
      lat: origin.gpsLat + deltaLat,
      lon: origin.gpsLon + deltaLon
    };
  }, [coordinateCalibration]);

  // Используем useMemo для стабилизации объекта возврата
  // Сравниваем selectedVehicles по содержимому, а не по ссылке
  const selectedVehiclesKey = JSON.stringify(selectedVehicles);
  return useMemo(() => ({
    coordinateCalibration,
    setCoordinateCalibration,
    selectedVehicles,
    setSelectedVehicles,
    saveSettings,
    transformGPStoCanvas,
    transformCanvasToGPS,
  }), [coordinateCalibration, selectedVehiclesKey, setCoordinateCalibration, setSelectedVehicles, saveSettings, transformGPStoCanvas, transformCanvasToGPS]);
}


