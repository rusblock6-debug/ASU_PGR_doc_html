/**
 * Копия хука из https://git.dmi-msk.ru/retek.pgr/dispatching/graph-service-frontend/
 * Используется, как временное решение для отображения данных в реальном времени.
 * Хук для WebSocket подключения и отслеживания транспортных средств.
 */
/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-argument */
import { useCallback, useEffect, useRef, useState } from 'react';

interface UseWebSocketOptions {
  onVehicleUpdate?: (position: VehiclePosition) => void;
  vehiclesList?: any[];
}

interface VehiclePosition {
  vehicle_id: number;
  name?: string; // Название машины из enterprise-service
  lat: number; // Оригинальные GPS координаты (широта)
  lon: number; // Оригинальные GPS координаты (долгота)
  height?: number;
  speed?: number; // Скорость (км/ч)
  weight?: number; // Вес груза (тонны)
  fuel?: number; // Уровень топлива (л или %)
  state?: string; // State Machine статус (idle, moving_empty, loading, etc.)
  tag?: {
    // Текущая метка из eKuiper события
    point_id: string;
    point_name: string;
    point_type: string;
  } | null;
  task_id?: string | null; // ID задания для получения маршрута
  trip_type?: 'planned' | 'unplanned' | null; // Тип рейса
  timestamp: number;
}

export function useWebSocket({ onVehicleUpdate, vehiclesList }: UseWebSocketOptions) {
  const [vehiclePosition, setVehiclePosition] = useState<VehiclePosition | null>(null);
  const [vehicles, setVehicles] = useState<Record<string, VehiclePosition>>({});
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  // Инициализация начальных позиций всех машин на "гараже" (только в серверном режиме)
  useEffect(() => {
    // Ждём пока загрузятся машины
    if (!vehiclesList || vehiclesList.length === 0) {
      return;
    }

    const garageGpsLat = 0;
    const garageGpsLon = 0;
    const garageHeight = 0;

    // Создаем начальные позиции для всех машин
    const initialVehicles: Record<string, VehiclePosition> = {};

    vehiclesList.forEach((vehicle) => {
      const vehicleKey = String(vehicle.id);
      initialVehicles[vehicleKey] = {
        vehicle_id: Number(vehicle.id),
        name: vehicle.name,
        lat: garageGpsLat,
        lon: garageGpsLon,
        height: garageHeight,
        timestamp: Date.now(),
        tag: null,
      };
    });

    setVehicles(initialVehicles);
  }, [vehiclesList]);

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
          const data: VehiclePosition = {
            ...(message.data as VehiclePosition),
            vehicle_id: Number(message.data.vehicle_id),
          };

          setVehicles((prev) => {
            const existingVehicle = prev[data.vehicle_id];

            // Обновляем позицию, сохраняя предыдущие данные (имя, и т.д.)
            // tag уже приходит из WebSocket — не нужно делать отдельный HTTP запрос
            const enrichedData: VehiclePosition = {
              ...existingVehicle,
              ...data,
              name: existingVehicle?.name || data.name,
            };

            setVehiclePosition(enrichedData);
            onVehicleUpdate?.(enrichedData);

            return {
              ...prev,
              [data.vehicle_id]: enrichedData,
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
