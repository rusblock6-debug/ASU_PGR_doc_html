/**
 * Хук для WebSocket подключения и отслеживания транспортных средств
 * Использует нативные WebSockets (FastAPI)
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import { VehiclePosition } from '../types/graph';
import { EnterpriseVehicle } from '../services/api';
import { useSettings } from './useSettings';

interface UseWebSocketOptions {
  searchHeight?: number;  // Высота для поиска меток (не используется, оставлено для совместимости)
  onVehicleUpdate?: (position: VehiclePosition) => void;
  vehiclesList?: EnterpriseVehicle[];  // Список машин из useVehicles (для инициализации)
}

export function useWebSocket({ onVehicleUpdate, vehiclesList }: UseWebSocketOptions) {
  const [vehiclePosition, setVehiclePosition] = useState<VehiclePosition | null>(null);
  const [vehicles, setVehicles] = useState<{[key: string]: VehiclePosition}>({});
  const [isConnected, setIsConnected] = useState(false);
  const settings = useSettings();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  // Инициализация начальных позиций всех машин на "гараже" (только в серверном режиме)
  useEffect(() => {
    const appMode = process.env.REACT_APP_MODE || 'server';
    
    // БОРТОВОЙ РЕЖИМ: не создаем машины на гараже
    if (appMode === 'onboard') {
      console.log('🚛 [WebSocket] Бортовой режим - ждем WebSocket данных');
      return;
    }
    
    // Ждём пока загрузятся машины
    if (!vehiclesList || vehiclesList.length === 0) {
      return;
    }
    
    // СЕРВЕРНЫЙ РЕЖИМ: создаем все машины на гараже
    console.log('🖥️ [WebSocket] Серверный режим - инициализация машин');
    
    // Получаем координаты гаража из env
    const garageGpsLat = parseFloat(process.env.REACT_APP_GARAGE_LAT || '0');
    const garageGpsLon = parseFloat(process.env.REACT_APP_GARAGE_LON || '0');
    const garageHeight = parseFloat(process.env.REACT_APP_GARAGE_HEIGHT || '0');
    
    // Преобразуем GPS в Canvas координаты
    const garageCanvas = settings.transformGPStoCanvas(garageGpsLat, garageGpsLon);
    
    console.log(`📍 [WebSocket] Инициализация ${vehiclesList.length} машин на гараже: GPS(${garageGpsLat}, ${garageGpsLon})`);
    
    // Создаем начальные позиции для всех машин
    const initialVehicles: {[key: string]: VehiclePosition} = {};
    
    vehiclesList.forEach(vehicle => {
      // Используем id как ключ (конвертируем в строку)
      const vehicleKey = String(vehicle.id);
      initialVehicles[vehicleKey] = {
        vehicle_id: vehicleKey,
        name: vehicle.name,
        lat: garageGpsLat,
        lon: garageGpsLon,
        canvasX: garageCanvas.x,
        canvasY: garageCanvas.y,
        height: garageHeight,
        rotation: 0,
        timestamp: Date.now(),
        tag: null,
        currentTag: null
      };
    });
    
    setVehicles(initialVehicles);
  }, [settings, vehiclesList]);

  // Функция подключения WebSocket
  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/vehicle-tracking`;
    
    console.log(`🔌 [WebSocket] Подключение к: ${wsUrl}`);
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('✅ [WebSocket] Подключено!');
      setIsConnected(true);
      reconnectAttemptsRef.current = 0;
    };
    
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        
        // Обработка vehicle_location_update
        if (message.type === 'vehicle_location_update') {
          const data = message.data as VehiclePosition;
          
          setVehicles(prev => {
            const existingVehicle = prev[data.vehicle_id];
            
            // Обновляем позицию, сохраняя предыдущие данные (имя, и т.д.)
            // tag уже приходит из WebSocket — не нужно делать отдельный HTTP запрос
            const enrichedData: VehiclePosition = {
              ...existingVehicle,
              ...data,
              name: existingVehicle?.name || data.name,
              state: data.state,
              task_id: data.task_id,
              trip_type: data.trip_type,
              tag: data.tag,  // Метка из WebSocket (от eKuiper)
              // Для обратной совместимости маппим tag на currentTag
              currentTag: data.tag ? {
                point_id: data.tag.point_id,
                point_name: data.tag.point_name,
                point_type: data.tag.point_type
              } : existingVehicle?.currentTag || null
            };
            
            setVehiclePosition(enrichedData);
            onVehicleUpdate?.(enrichedData);
            
            return {
              ...prev,
              [data.vehicle_id]: enrichedData
            };
          });
        }
      } catch (error) {
        console.error('❌ [WebSocket] Ошибка парсинга сообщения:', error);
      }
    };
    
    ws.onclose = (event) => {
      console.warn(`⚠️ [WebSocket] Отключено. Code: ${event.code}`);
      setIsConnected(false);
      wsRef.current = null;
      
      // Переподключение
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current++;
        const delay = 1000 * reconnectAttemptsRef.current;
        console.log(`🔄 [WebSocket] Переподключение через ${delay}мс (попытка ${reconnectAttemptsRef.current})`);
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      }
    };
    
    ws.onerror = (error) => {
      console.error('❌ [WebSocket] Ошибка:', error);
    };
    
    wsRef.current = ws;
  }, [onVehicleUpdate]);

  useEffect(() => {
    connect();
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);


  const clearVehicles = useCallback(() => {
    setVehicles({});
    setVehiclePosition(null);
  }, []);

  return {
    vehiclePosition,
    vehicles,
    isConnected,
    clearVehicles,
  };
}
