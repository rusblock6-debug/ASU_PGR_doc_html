/**
 * 3D визуализация графа с использованием Three.js
 */
import React, { useEffect, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { getHorizons, getHorizonGraph } from '../services/api';
import { Horizon, GraphData, GraphNode, GraphEdge, Tag, Place, VehiclePosition } from '../types/graph';
import { NodeSphere, EdgeLine, SpiralEdge, TagSphere, PlaceSphere, VehicleSphere } from './three';
import { useSettings, useVehicles } from '../hooks';
import { VehiclePanel } from './VehiclePanel';
import { preloadBelazModel } from '../utils/modelLoader';
import './ThreeView.css';

interface ThreeViewProps {}

// Основной компонент 3D сцены
const VEHICLES_PANEL_WIDTH = 300;

function ThreeScene({ graphData, vehicles, horizons, controlsRef, selectedHorizon, onCameraChange, followingVehicleId, isUserInteractingRef, lastCameraUpdateRef, graphCenter, vehicleFirstTeleportPending, onFirstTeleportDone }: { 
  graphData: GraphData | null, 
  vehicles: {[key: string]: VehiclePosition}, 
  horizons: Horizon[], 
  controlsRef: React.RefObject<any>, 
  selectedHorizon: Horizon | null,
  onCameraChange?: (distance: number) => void,
  followingVehicleId: string | null,
  isUserInteractingRef: React.MutableRefObject<boolean>,
  lastCameraUpdateRef: React.MutableRefObject<number>,
  graphCenter: THREE.Vector3 | null;
  vehicleFirstTeleportPending?: Set<string>;
  onFirstTeleportDone?: (vehicleId: string) => void;
}) {
  // Гарантируем, что horizons всегда массив
  const safeHorizons = Array.isArray(horizons) ? horizons : [];
  const settings = useSettings();
  
  // Компонент для отслеживания камеры за машиной (ПРОСТОЕ СЛЕДОВАНИЕ)
  function CameraFollower() {
    const { scene } = useThree();
    const lastFollowingId = useRef<string | null>(null);
    const lastTargetPos = useRef<THREE.Vector3 | null>(null);
    
    useFrame(() => {
      if (!followingVehicleId || !controlsRef.current) {
        if (lastFollowingId.current !== null) {
          lastFollowingId.current = null;
          lastTargetPos.current = null;
        }
        return;
      }
      
      // Если сменили машину - сбрасываем состояние
      if (lastFollowingId.current !== followingVehicleId) {
        lastFollowingId.current = followingVehicleId;
        lastTargetPos.current = null;
      }
      
      // Ищем 3D модель машины в сцене
      const vehicleModel = scene.getObjectByName(`vehicle-${followingVehicleId}`);
      if (!vehicleModel) return;
      
      const controls = controlsRef.current;
      const camera = controls.object;
      
      // Получаем текущую позицию модели
      const vehicleWorldPos = new THREE.Vector3();
      vehicleModel.getWorldPosition(vehicleWorldPos);
      
      // Новая позиция target (чуть выше машины)
      const newTargetPos = vehicleWorldPos.clone();
      newTargetPos.y += 5;
      
      // Если есть предыдущая позиция - вычисляем смещение
      if (lastTargetPos.current) {
        const delta = new THREE.Vector3();
        delta.subVectors(newTargetPos, lastTargetPos.current);
        
        // Смещаем и target и камеру на одинаковое расстояние
        // (это сохраняет относительную позицию камеры вокруг машины)
        controls.target.add(delta);
        camera.position.add(delta);
      } else {
        // Первый кадр - просто устанавливаем target
        controls.target.copy(newTargetPos);
      }
      
      // Сохраняем текущую позицию для следующего кадра
      lastTargetPos.current = newTargetPos.clone();
      
      controls.update();
    });
    
    return null;
  }
  
  // Создаём мапу horizon_id → color для быстрого доступа
  const levelColors = React.useMemo(() => {
    const map: {[key: number]: string} = {};
    safeHorizons.forEach(level => {
      map[level.id] = level.color || '#2196F3';  // дефолтный цвет если не задан
    });
    return map;
  }, [safeHorizons]);

  // Кэшируем мапу узлов для быстрого поиска (оптимизация)
  const nodeMap = React.useMemo(() => {
    const map = new Map<number, GraphNode>();
    graphData?.nodes.forEach(node => {
      map.set(node.id, node);
    });
    return map;
  }, [graphData]);


  // Убрана лишняя проверка controlsRef - она дублирует проверку в ThreeView

  // Проверяем, что graphData существует И имеет данные
  const hasNodes = graphData?.nodes && Array.isArray(graphData.nodes) && graphData.nodes.length > 0;
  const hasEdges = graphData?.edges && Array.isArray(graphData.edges);
  const hasTags = graphData?.tags && Array.isArray(graphData.tags);
  const hasPlaces = graphData?.places && Array.isArray(graphData.places) && graphData.places.length > 0;

  const placeRadiusMap = React.useMemo(() => {
    const m = new Map<number, number>();
    (graphData?.tags || []).forEach((t) => {
      if (!t.place_id) return;
      const r = t.radius || 25;
      const prev = m.get(t.place_id) ?? 0;
      m.set(t.place_id, Math.max(prev, r));
    });
    return m;
  }, [graphData?.tags]);
  
  // НЕ возвращаем null даже если нет данных - OrbitControls должен монтироваться для инициализации камеры
  // Рендерим только OrbitControls если нет данных, чтобы controlsRef установился
  if (!graphData || !hasNodes) {
    return (
      <>
        <ambientLight intensity={0.7} />
        <OrbitControls 
          ref={controlsRef}
          enableDamping
          dampingFactor={0.15}
          rotateSpeed={0.5}
          zoomSpeed={3.5}
          panSpeed={1.0}
          minDistance={5}
          maxDistance={5000}
          enableZoom={true}
          zoomToCursor={false}
          autoRotate={false}
          enablePan={true}
          enableRotate={true}
          onStart={() => {
            if (controlsRef.current) {
              controlsRef.current.enableZoom = true;
            }
            // Устанавливаем флаг активного взаимодействия пользователя
            isUserInteractingRef.current = true;
          }}
          onChange={(e) => {
            // ОПТИМИЗАЦИЯ: Увеличено throttling до 200мс для снижения нагрузки при активном взаимодействии
            const now = Date.now();
            if (onCameraChange && controlsRef.current && lastCameraUpdateRef.current !== null && now - lastCameraUpdateRef.current > 200) {
              const camera = controlsRef.current.object;
              const target = controlsRef.current.target;
              const distance = camera.position.distanceTo(target);
              onCameraChange(Math.round(distance));
              lastCameraUpdateRef.current = now;
            }
          }}
          onEnd={() => {
            // ОПТИМИЗАЦИЯ: Уменьшена задержка сброса флага, т.к. damping factor увеличен (быстрее затухает)
            setTimeout(() => {
              isUserInteractingRef.current = false;
            }, 150);  // Уменьшено с 350мс до 150мс, т.к. damping factor увеличен до 0.15
          }}
        />
      </>
    );
  }


  return (
    <>
      {/* Оптимизированное освещение - меньше источников */}
      <ambientLight intensity={0.7} />
      <directionalLight position={[50, 50, 50]} intensity={0.6} />
      <hemisphereLight args={['#87CEEB', '#8B4513', 0.2]} />

      {/* Ребра графа */}
      {graphData.edges.map((edge) => {
        const fromNode = nodeMap.get(edge.from_node_id);
        const toNode = nodeMap.get(edge.to_node_id);
        
        // 🔍 DEBUG: Логируем отсутствующие узлы для вертикальных рёбер (только в development)
        
        if (fromNode && toNode) {
          // Используем винтообразное ребро для вертикальных соединений (лестниц)
          if (edge.edge_type === 'vertical') {
            return (
              <SpiralEdge
                key={edge.id}
                fromNode={fromNode}
                toNode={toNode}
                levelColor={levelColors[fromNode.horizon_id]}
              />
            );
          }
          
          // Обычное ребро для горизонтальных соединений
          return (
            <EdgeLine
              key={edge.id}
              fromNode={fromNode}
              toNode={toNode}
              levelColor={levelColors[fromNode.horizon_id]}
            />
          );
        }
        return null;
      })}

      {/* Узлы графа */}
      {graphData.nodes.map((node) => (
        <NodeSphere key={node.id} node={node} />
      ))}

      {/* Места (предпочтительный источник координат) */}
      {hasPlaces
        ? (graphData.places as Place[]).map((place) => (
            <PlaceSphere
              key={`place-${place.id}`}
              place={place}
              height={safeHorizons.find((h) => h.id === (place.horizon_id ?? place.horizon?.id))?.height ?? 0}
              radius={placeRadiusMap.get(place.id)}
              transformGPStoCanvas={settings.transformGPStoCanvas}
            />
          ))
        : graphData.tags.map((tag) => <TagSphere key={`tag-${tag.id}`} tag={tag} />)}

      {/* Транспортные средства (скрываем на других уровнях в режиме редактирования) */}
      {Object.values(vehicles).map((vehicle) => {
        // Если выбран уровень (режим редактирования) - показываем только машины на этом уровне
        if (selectedHorizon) {
          // Если высота не указана - не показываем машину (не знаем на каком она уровне)
          const vehicleHeight = vehicle.height;
          if (vehicleHeight === undefined || vehicleHeight === null) {
            return null;
          }
          // Ищем уровень по высоте машины
          const vehicleHorizon = safeHorizons.find(l => Math.abs(l.height - vehicleHeight) < 5);
          if (!vehicleHorizon || vehicleHorizon.id !== selectedHorizon.id) {
            return null; // Машина на другом уровне - не показываем
          }
        }
        
        return (
          <VehicleSphere
            key={vehicle.vehicle_id}
            vehicle={vehicle}
            teleportToTarget={vehicleFirstTeleportPending?.has(vehicle.vehicle_id)}
            onFirstTeleportDone={onFirstTeleportDone}
          />
        );
      })}

      {/* Компонент для следования камеры за машиной */}
      <CameraFollower />

      {/* Управление камерой с улучшенными настройками */}
      <OrbitControls 
        ref={controlsRef}
        enableDamping
        dampingFactor={0.15}
        rotateSpeed={0.5}
        zoomSpeed={3.5}
        panSpeed={1.0}
        minDistance={5}
        maxDistance={5000}
        enableZoom={true}
        zoomToCursor={false}
        autoRotate={false}
        enablePan={true}  // Панорамирование ВСЕГДА включено (нужно для правой кнопки!)
        enableRotate={true}  // Вращение всегда включено
        mouseButtons={{
          LEFT: followingVehicleId ? -1 : 0,   // При следовании: отключена, иначе: вращение (THREE.MOUSE.ROTATE = 0)
          MIDDLE: 1,  // Колёсико = zoom (THREE.MOUSE.DOLLY = 1)
          RIGHT: followingVehicleId ? 0 : 2    // При следовании: вращение (0 = ROTATE), иначе: панорамирование (2 = PAN)
        }}
        onStart={(e) => {
          // При начале взаимодействия с камерой - убеждаемся что зум включен
          if (controlsRef.current) {
            controlsRef.current.enableZoom = true;
          }
          // Устанавливаем флаг активного взаимодействия пользователя
          isUserInteractingRef.current = true;
        }}
        onChange={(e) => {
          // При изменении камеры (зум колёсиком или вращение) обновляем дистанцию
          const now = Date.now();
          if (controlsRef.current) {
            const camera = controlsRef.current.object;
            const target = controlsRef.current.target;
            const distance = camera.position.distanceTo(target);
            
            if (onCameraChange && lastCameraUpdateRef.current !== null && now - lastCameraUpdateRef.current > 200) {
              onCameraChange(Math.round(distance));
              lastCameraUpdateRef.current = now;
            }
          }
        }}
        onEnd={() => {
          // ОПТИМИЗАЦИЯ: Уменьшена задержка сброса флага, т.к. damping factor увеличен (быстрее затухает)
          setTimeout(() => {
            isUserInteractingRef.current = false;
          }, 150);  // Уменьшено с 350мс до 150мс, т.к. damping factor увеличен до 0.15
        }}
      />
    </>
  );
}

const ThreeView: React.FC<ThreeViewProps> = () => {
  const [horizons, setHorizons] = useState<Horizon[]>([]);
  const [selectedHorizon, setSelectedHorizon] = useState<Horizon | null>(null);  // ДОЛЖЕН БЫТЬ NULL В РЕЖИМЕ "ПРОСМОТР"!
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [vehiclePosition, setVehiclePosition] = useState<VehiclePosition | null>(null);
  const [allGraphData, setAllGraphData] = useState<GraphData | null>(null);
  const [vehicles, setVehicles] = useState<{[key: string]: VehiclePosition}>({});
  const [vehicleNamesMap, setVehicleNamesMap] = useState<Map<string, string>>(new Map());
  const vehicleNamesMapRef = useRef<Map<string, string>>(new Map());
  const [isVehiclePanelOpen, setIsVehiclePanelOpen] = useState(false);
  const [followingVehicleId, setFollowingVehicleId] = useState<string | null>(null);  // ID машины для отслеживания
  const followingVehicleIdRef = useRef<string | null>(null);  // Ref для доступа к актуальному значению в замыканиях
  const [cameraLocked, setCameraLocked] = useState(false);  // Флаг блокировки автоматической камеры при слежении
  const cameraLockedRef = useRef<boolean>(false);  // Ref для доступа к актуальному значению в замыканиях
  const [cameraMode, setCameraMode] = useState<'top' | 'front' | 'side' | 'iso'>('iso');  // Текущий режим камеры
  

  // Синхронизация ref со state для использования в замыканиях WebSocket
  useEffect(() => {
    followingVehicleIdRef.current = followingVehicleId;
    
    // При смене followingVehicleId - сбрасываем offset камеры
    // Это заставит CameraFollower пересчитать offset в следующем кадре
    if (followingVehicleId === null) {
      // Сброс при отключении следования
      // Находим ThreeScene и сбрасываем offset через ref (не через state)
      // Доступ к ref компонента ThreeScene
      // (офсет сбросится в CameraFollower при следующей проверке followingVehicleId)
    }
  }, [followingVehicleId]);

  useEffect(() => {
    cameraLockedRef.current = cameraLocked;
  }, [cameraLocked]);
  const [cameraDistance, setCameraDistance] = useState(50);  // Дистанция камеры от машины (зум)
  const [graphCenterState, setGraphCenterState] = useState<THREE.Vector3 | null>(null);  // Состояние центра графа для визуализации
  const [isCameraReady, setIsCameraReady] = useState(false);  // Флаг готовности камеры (скрываем сцену до установки)
  const [isLoading, setIsLoading] = useState(true);  // Общий флаг загрузки
  const socketRef = useRef<WebSocket | null>(null);
  const isUserInteractingRef = useRef(false);  // Флаг активного взаимодействия пользователя с камерой
  const lastCameraUpdateRef = useRef<number>(0);  // Время последнего обновления камеры (для throttling)
  /** Машины, для которых пришло первое обновление по WebSocket — один раз телепортируем, потом плавное движение */
  const [vehicleFirstTeleportPending, setVehicleFirstTeleportPending] = useState<Set<string>>(new Set());
  const vehiclesWsUpdateReceivedRef = useRef<Set<string>>(new Set());
  
  // Используем хук настроек для GPS трансформации
  const settings = useSettings();
  
  
  // ВАЖНО: В режиме "Просмотр" selectedHorizon ДОЛЖЕН быть null, чтобы показывать ВСЕ уровни!
  useEffect(() => {
    // КРИТИЧЕСКИЙ FIX: Проверяем версию настроек координат в localStorage
    // ВЕРСИЯ 4: canvasZ = 0, enabled = true (ВКЛЮЧЕНА!)
    const storedCalibration = localStorage.getItem('coordinateCalibration');
    if (storedCalibration) {
      try {
        const parsed = JSON.parse(storedCalibration);
        
        // Проверяем:
        // 1. Origin Point правильный (центр 58.173161, 59.818738)
        // 2. canvasZ = 0 (не -25)
        // 3. enabled = true (калибровка ВКЛЮЧЕНА - узлы в GPS!)
        const isOldVersion = !parsed.origin || 
                            Math.abs(parsed.origin.gpsLat - 58.173161) > 0.0001 ||
                            Math.abs(parsed.origin.gpsLon - 59.818738) > 0.001 ||
                            parsed.origin.canvasZ !== 0 ||
                            parsed.enabled !== true;
        
        if (isOldVersion) {
          localStorage.removeItem('coordinateCalibration');
          window.location.reload(); // Перезагружаем для применения НОВЫХ настроек
          return;
        }
      } catch (e) {
        console.error('Ошибка парсинга coordinateCalibration:', e);
        localStorage.removeItem('coordinateCalibration');
        window.location.reload();
        return;
      }
    }
    
    if (selectedHorizon !== null) {
      setSelectedHorizon(null);
    }
  }, []);

  // Загрузка уровней
  useEffect(() => {
    loadHorizons();
  }, []);

  // Используем централизованный хук для загрузки машин
  const { vehicles: enterpriseVehicles } = useVehicles(1);
  
  // Создание начальных позиций машин на "гараже" (только в серверном режиме)
  useEffect(() => {
    const appMode = process.env.REACT_APP_MODE || 'server';
    
    if (!enterpriseVehicles || enterpriseVehicles.length === 0) {
      return;
    }
    
    // Создаем мапу названий (нужна в обоих режимах)
    const namesMap = new Map<string, string>();
    enterpriseVehicles.forEach(vehicle => {
      // Используем id как ключ
      namesMap.set(String(vehicle.id), vehicle.name);
    });
    setVehicleNamesMap(namesMap);
    vehicleNamesMapRef.current = namesMap;
    
    // СЕРВЕРНЫЙ РЕЖИМ: создаем все машины на гараже
    if (appMode === 'server') {
      console.log('🖥️ [Mode] Серверный режим - инициализация всех машин на гараже');
      
      // Получаем начальные координаты "гаража" из env переменных
      const garageGpsLat = parseFloat(process.env.REACT_APP_GARAGE_LAT || '0');
      const garageGpsLon = parseFloat(process.env.REACT_APP_GARAGE_LON || '0');
      const garageHeight = parseFloat(process.env.REACT_APP_GARAGE_HEIGHT || '0');
      
      // Преобразуем GPS координаты гаража в Canvas координаты
      const garageCanvas = settings.transformGPStoCanvas(garageGpsLat, garageGpsLon);
      
      console.log(`📍 [Vehicles] Начальная позиция гаража: GPS(${garageGpsLat}, ${garageGpsLon}) → Canvas(${garageCanvas.x.toFixed(2)}, ${garageCanvas.y.toFixed(2)}), высота: ${garageHeight}`);
      
      // Создаем начальные позиции для всех машин на гараже
      const initialVehicles: {[key: string]: VehiclePosition} = {};
      
      enterpriseVehicles.forEach(vehicle => {
        // Используем id как ключ
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
          currentTag: null
        };
      });
      
      setVehicles(initialVehicles);
      console.log(`✅ [Vehicles] Создано ${enterpriseVehicles.length} машин на начальной позиции`);
    } 
    // БОРТОВОЙ РЕЖИМ: НЕ создаем машины, ждем WebSocket данных
    else if (appMode === 'onboard') {
      console.log('🚛 [Mode] Бортовой режим - машины появятся только при получении WebSocket данных');
    }
  }, [settings, enterpriseVehicles]);

    // Предзагружаем модель Belaz только в 3D режиме
  useEffect(() => {
    const startTime = performance.now();
    
    preloadBelazModel()
      .then(() => {
        const loadTime = (performance.now() - startTime).toFixed(0);
        console.log(`✅ [Model Load] 3D модели загружены за ${loadTime}мс`);
      })
      .catch((error) => {
        console.error('❌ [Model Load] Failed to preload Belaz model:', error);
      });
  }, []);

  const loadHorizons = async () => {
    try {
      const horizonsData = await getHorizons();
      setHorizons(horizonsData);
      // НЕ УСТАНАВЛИВАЕМ selectedHorizon! В режиме "Просмотр" он должен быть null!
      // if (horizonsData.length > 0) {
      //   setSelectedHorizon(horizonsData[0]);  // ❌ УДАЛЕНО - это вызывало скрытие машины!
      // }
    } catch (error) {
      console.error('Error loading horizons:', error);
    }
  };

  // Загрузка всех уровней для 3D визуализации
  useEffect(() => {
    if (horizons.length > 0) {
      // Сбрасываем флаг инициализации камеры при загрузке новых данных графа
      cameraInitialized.current = false;
      setIsCameraReady(false); // Скрываем сцену до установки камеры
      loadAllHorizonsData();
    }
  }, [horizons]);

  const loadAllHorizonsData = async () => {
    try {
      const startTime = performance.now();
      
      // Инициализируем пустые данные
      setAllGraphData({
        nodes: [],
        edges: [],
        tags: [],
        places: [],
      });

      // Загружаем горизонты параллельно
      const safeHorizonsList = Array.isArray(horizons) ? horizons : [];
      const results = await Promise.allSettled(
        safeHorizonsList.map(async (level) => {
          try {
            return await getHorizonGraph(level.id);
          } catch (error) {
            return null;
          }
        })
      );
      
      // Собираем все успешно загруженные данные
      const allNodes: GraphNode[] = [];
      const allEdges: GraphEdge[] = [];
      const allTags: Tag[] = [];
      const allPlaces: Place[] = [];
      const edgeMap = new Map<number, GraphEdge>();
      
      results.forEach((result) => {
        if (result.status === 'fulfilled' && result.value) {
          const data = result.value;
          allNodes.push(...data.nodes);
          data.edges.forEach(edge => {
            edgeMap.set(edge.id, edge);
          });
          allTags.push(...data.tags);
          if (Array.isArray(data.places)) {
            allPlaces.push(...data.places);
          }
        }
      });

      // Обновляем состояние один раз с полными данными
      const loadTime = (performance.now() - startTime).toFixed(0);
      console.log(`✅ [Graph Load] Загружено за ${loadTime}мс: ${allNodes.length} узлов, ${Array.from(edgeMap.values()).length} рёбер`);
      
      setAllGraphData({
        nodes: allNodes,
        edges: Array.from(edgeMap.values()),
        tags: allTags,
        places: allPlaces,
      });
      
    } catch (error) {
      console.error('❌ Error loading all horizons data:', error);
      // Устанавливаем пустые данные при ошибке, чтобы не блокировать интерфейс
      setAllGraphData({
        nodes: [],
        edges: [],
        tags: [],
        places: [],
      });
    }
  };

  // WebSocket подключение для отслеживания транспортных средств (нативный WebSocket)
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/vehicle-tracking`;
    console.log(`🔌 [WebSocket] Подключение к: ${wsUrl}`);
    
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    let reconnectTimeout: NodeJS.Timeout | null = null;
    
    const connect = () => {
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('✅ [WebSocket] Подключено!');
        reconnectAttempts = 0;
      };
      
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          // Обработка vehicle_location_update
          if (message.type === 'vehicle_location_update') {
            const data = message.data as VehiclePosition;
            const isFirstUpdate = !vehiclesWsUpdateReceivedRef.current.has(data.vehicle_id);
            if (isFirstUpdate) {
              vehiclesWsUpdateReceivedRef.current.add(data.vehicle_id);
              setVehicleFirstTeleportPending(prev => new Set(prev).add(data.vehicle_id));
            }

            // Backend уже отправляет canvasX и canvasY, но если их нет - делаем трансформацию на фронте
            const canvasX = data.canvasX ?? settings.transformGPStoCanvas(data.lat, data.lon).x;
            const canvasY = data.canvasY ?? settings.transformGPStoCanvas(data.lat, data.lon).y;

            // Используем функциональное обновление для получения актуального предыдущего состояния
            setVehicles(prev => {
              const prevVehicle = prev[data.vehicle_id];
              // Получаем название машины из мапы (используем ref для актуального значения)
              const vehicleName = vehicleNamesMapRef.current.get(data.vehicle_id) || prevVehicle?.name;
              
              // Вычисляем угол поворота на основе движения
              let rotation = prevVehicle?.rotation ?? 0;
              
              if (prevVehicle && prevVehicle.canvasX !== undefined && prevVehicle.canvasY !== undefined) {
                const dx = canvasX - prevVehicle.canvasX;
                const dy = canvasY - prevVehicle.canvasY;
                
                // Вычисляем угол только если машина движется (минимальное смещение 0.5м)
                if (Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5) {
                  rotation = Math.atan2(dy, dx);
                }
              }
              
              // Создаем позицию с оригинальными GPS координатами И Canvas координатами для 3D
              // tag уже приходит из WebSocket — не нужно делать отдельный HTTP запрос
              const vehicleData: VehiclePosition = {
                ...data,
                name: vehicleName,
                lat: data.lat,
                lon: data.lon,
                canvasX,
                canvasY,
                prevCanvasX: prevVehicle?.canvasX,
                prevCanvasY: prevVehicle?.canvasY,
                rotation,
                height: data.height,
                tag: data.tag,  // Метка из WebSocket (от eKuiper)
                // Для обратной совместимости маппим tag на currentTag
                currentTag: data.tag ? {
                  point_id: data.tag.point_id,
                  point_name: data.tag.point_name,
                  point_type: data.tag.point_type
                } : prevVehicle?.currentTag || null
              };
              
              setVehiclePosition(vehicleData);
              
              return {
                ...prev,
                [data.vehicle_id]: vehicleData
              };
            });
          }
        } catch (error) {
          console.error('❌ [WebSocket] Ошибка парсинга сообщения:', error);
        }
      };
      
      ws.onclose = (event) => {
        console.warn(`⚠️ [WebSocket] Отключено. Code: ${event.code}`);
        socketRef.current = null;
        
        // Переподключение
        if (reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts++;
          const delay = 1000 * reconnectAttempts;
          console.log(`🔄 [WebSocket] Переподключение через ${delay}мс (попытка ${reconnectAttempts})`);
          reconnectTimeout = setTimeout(connect, delay);
        }
      };
      
      ws.onerror = (error) => {
        console.error('❌ [WebSocket] Ошибка:', error);
      };
      
      socketRef.current = ws;
    };
    
    connect();

    return () => {
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [settings.transformGPStoCanvas]);


  const controlsRef = useRef<any>(null);
  const cameraInitialized = useRef(false); // Флаг для предотвращения повторной установки камеры
  const controlsReadyCallback = useRef<((controls: any) => void) | null>(null); // Callback для готовности OrbitControls
  const defaultCameraPosition = useRef<THREE.Vector3 | null>(null); // Дефолтная изометрическая позиция камеры
  const defaultCameraTarget = useRef<THREE.Vector3 | null>(null); // Дефолтная цель камеры (центр графа)

  // Preset camera views
  const setCameraView = (view: 'top' | 'front' | 'side' | 'iso' | 'reset' | 'vehicles') => {
    if (!controlsRef.current) return;
    
    // Сохраняем режим камеры (кроме 'reset' и 'vehicles')
    if (view !== 'reset' && view !== 'vehicles') {
      setCameraMode(view);
    }
    
    // RESET - сбрасываем отслеживание машины
    if (view === 'reset') {
      setFollowingVehicleId(null);
      setCameraLocked(false);
    }
    
    // При смене вида РАЗБЛОКИРУЕМ камеру для следования за машиной в новом режиме
    if (followingVehicleId && view !== 'vehicles' && view !== 'reset') {
      setCameraLocked(false);  // Разблокируем для применения нового режима
    }
    
    const camera = controlsRef.current.object;
    const controls = controlsRef.current;
    
    // Специальный режим для центрирования на грузовиках
    if (view === 'vehicles') {
      centerOnVehicles();
      return;
    }
    
    // Определяем центр - либо машина (если следим), либо граф
    let center = new THREE.Vector3(0, 0, 0);
    
    if (followingVehicleId && vehicles[followingVehicleId]) {
      // Если следим за машиной - центр на ней
      const vehicle = vehicles[followingVehicleId];
      const canvasX = vehicle.canvasX ?? settings.transformGPStoCanvas(vehicle.lat, vehicle.lon).x;
      const canvasY = vehicle.canvasY ?? settings.transformGPStoCanvas(vehicle.lat, vehicle.lon).y;
      center = new THREE.Vector3(canvasX, vehicle.height ?? 0, -canvasY);  // Для визуализации
    } else if (allGraphData && allGraphData.nodes.length > 0) {
      // Иначе центр на графе
      allGraphData.nodes.forEach(node => {
        const canvasCoords = settings.transformGPStoCanvas(node.y, node.x);
        center.x += canvasCoords.x;
        center.y += node.z;
        center.z += -canvasCoords.y;
      });
      center.divideScalar(allGraphData.nodes.length);
    }
    
    // Используем cameraDistance если следим за машиной, иначе умеренная дистанция для всех уровней
    const distance = followingVehicleId ? cameraDistance : 300;
    
    switch (view) {
      case 'top':
        camera.position.set(center.x, center.y + distance, center.z);
        break;
      case 'front':
        camera.position.set(center.x, center.y, center.z + distance);
        break;
      case 'side':
        camera.position.set(center.x + distance, center.y, center.z);
        break;
      case 'iso':
        // Возвращаем камеру к дефолтному изометрическому положению
        if (defaultCameraPosition.current && defaultCameraTarget.current) {
          camera.position.copy(defaultCameraPosition.current);
          controls.target.copy(defaultCameraTarget.current);
        } else {
          // Если дефолтное положение не сохранено, вычисляем изометрию как обычно
          const isoOffset = distance * 0.577;
          camera.position.set(center.x + isoOffset, center.y + isoOffset, center.z + isoOffset);
          controls.target.copy(center);
        }
        break;
      case 'reset':
        camera.position.set(80, 60, 80);
        controls.target.set(0, 0, 0);
        break;
    }
    
    if (view !== 'reset') {
      controls.target.copy(center);
    }
    
    controls.update();
  };

  // Вычисляем центр и границы графа для центрирования камеры (ТОЛЬКО ОДИН РАЗ!)
  useEffect(() => {
    // Если данные еще не загружены или камера уже инициализирована - выходим
    if (!allGraphData || allGraphData.nodes.length === 0 || cameraInitialized.current) {
      return;
    }
    
    // Ждем 100мс для стабилизации данных и монтирования компонентов
    const setupCameraTimeout = setTimeout(() => {
      // Двойная проверка после задержки
      if (cameraInitialized.current || !allGraphData || allGraphData.nodes.length === 0) {
        return;
      }
      
      let checkAttempts = 0;
      
      // Ждем полной инициализации OrbitControls (минимум 8 проверок = 40мс)
      let controlsReadyCount = 0;
      const checkControls = setInterval(() => {
        checkAttempts++;
        
        if (controlsRef.current) {
          controlsReadyCount++;
          
          // Ждем 8 проверок (40мс) для гарантии полной инициализации
          if (controlsReadyCount >= 8 && !cameraInitialized.current) {
            clearInterval(checkControls);
            
            // Проверка состояния OrbitControls
            if (!controlsRef.current.object || !controlsRef.current.target) {
              console.error('❌ [Camera Setup] OrbitControls не инициализирован');
              return;
            }
            
            // Преобразуем GPS координаты узлов в Canvas координаты
            const canvasCoords = allGraphData.nodes
              .map(n => {
                const coords = settings.transformGPStoCanvas(n.y, n.x);
                if (Math.abs(coords.x) > 100000 || Math.abs(coords.y) > 100000) {
                  return null;
                }
                return coords;
              })
              .filter(c => c !== null) as {x: number, y: number}[];
            
            if (canvasCoords.length === 0) {
              console.error('❌ [Camera Setup] Нет валидных узлов для центрирования');
              return;
            }
            
            // Вычисляем центр графа
            const xs = canvasCoords.map(c => c.x);
            const ys = canvasCoords.map(c => c.y);
            const zs = allGraphData.nodes.map(n => n.z);
            
            const centerX = (Math.max(...xs) + Math.min(...xs)) / 2;
            const centerY = (Math.max(...ys) + Math.min(...ys)) / 2;
            const centerZ = (Math.max(...zs) + Math.min(...zs)) / 2;
            
            // Вычисляем изометрическую позицию камеры
            const center = new THREE.Vector3(centerX, centerZ, -centerY);
            const distance = 300;
            const isoOffset = distance * 0.577; // offset = distance / √3
            
            const defaultPosition = new THREE.Vector3(
              center.x + isoOffset,
              center.y + isoOffset,
              center.z + isoOffset
            );
            
            // Сохраняем позиции
            defaultCameraPosition.current = defaultPosition.clone();
            defaultCameraTarget.current = center.clone();
            setGraphCenterState(center.clone());
            
            const camera = controlsRef.current.object;
            const controls = controlsRef.current;
            
            // Устанавливаем камеру
            const wasDampingEnabled = controls.enableDamping;
            controls.enableDamping = false;
            
            // Сбрасываем внутренние скорости OrbitControls
            if ('dollyDelta' in controls) (controls as any).dollyDelta = 0;
            if ('rotateDelta' in controls) (controls as any).rotateDelta = new THREE.Vector2(0, 0);
            if ('panDelta' in controls) (controls as any).panDelta = new THREE.Vector2(0, 0);
            if ('sphericalDelta' in controls) (controls as any).sphericalDelta = new THREE.Spherical(0, 0, 0);
            
            // Устанавливаем позицию и цель
            controls.target.copy(center);
            camera.position.copy(defaultPosition);
            controls.update();
            
            // Включаем damping обратно
            controls.enableDamping = wasDampingEnabled;
            controls.update();
            
            setCameraMode('iso'); // Устанавливаем режим камеры в изометрию
            cameraInitialized.current = true; // Отмечаем что камера установлена
            setIsCameraReady(true); // Показываем сцену - камера готова
            setIsLoading(false); // Скрываем индикатор загрузки
            
            console.log('✅ [Camera Setup] Камера установлена в изометрическое положение');
          }
        }
      }, 5); // ОПТИМИЗИРОВАНО: Проверяем каждые 5мс для более быстрой инициализации (было 10мс)
      
      // Сохраняем intervalId для очистки
      let intervalId: NodeJS.Timeout | null = checkControls;
      
      // Cleanup: возвращаем функцию для очистки interval
      return () => {
        if (intervalId) {
          clearInterval(intervalId);
        }
      };
    }, 100); // ОПТИМИЗИРОВАНО: Уменьшено с 300мс до 100мс для более быстрой инициализации
    
    // Cleanup: очищаем timeout при размонтировании или изменении зависимостей
    return () => {
      clearTimeout(setupCameraTimeout);
    };
  }, [allGraphData, settings]);


  // 🔍 DEBUG: Логируем allGraphData перед передачей в ThreeScene (только в development)
  React.useEffect(() => {
  }, [allGraphData]);

  const handleBackToEditor = () => {
    window.location.href = '/2d';
  };

  // Центрирование камеры на машину (простое следование без автоповорота)
  const centerOnVehicle3D = (vehicle: VehiclePosition) => {
    if (!controlsRef.current) return;
    
    const camera = controlsRef.current.object;
    const controls = controlsRef.current;
    
    // Используем canvasX/canvasY если есть, иначе трансформируем GPS координаты
    let canvasX = vehicle.canvasX;
    let canvasY = vehicle.canvasY;
    
    if (canvasX === undefined || canvasY === undefined) {
      const transformed = settings.transformGPStoCanvas(vehicle.lat, vehicle.lon);
      canvasX = transformed.x;
      canvasY = transformed.y;
    }
    
    // В 3D: X=canvasX, Y=height, Z=-canvasY
    const vehiclePos = new THREE.Vector3(
      canvasX,
      vehicle.height ?? 0,
      -canvasY
    );
    
    // Простая позиция: позади и сверху (без привязки к направлению)
    const distance = 50;
    const height = 30;
    
    const cameraPos = new THREE.Vector3(
      vehiclePos.x - distance,
      vehiclePos.y + height,
      vehiclePos.z
    );
    
    const targetPos = vehiclePos.clone();
    targetPos.y += 5;  // Немного выше машины
    
    camera.position.copy(cameraPos);
    controls.target.copy(targetPos);
    controls.update();
    
    // Включаем режим слежения за машиной
    setFollowingVehicleId(vehicle.vehicle_id);
    setCameraLocked(false);
  };

  // Center camera on all vehicles
  const centerOnVehicles = () => {
    if (!controlsRef.current) return;
    
    const vehicleList = Object.values(vehicles);
    if (vehicleList.length === 0) {
      return;
    }
    
    const camera = controlsRef.current.object;
    const controls = controlsRef.current;
    
    // Вычисляем центр всех грузовиков
    const center = new THREE.Vector3(0, 0, 0);
    vehicleList.forEach(vehicle => {
      const transformed = settings.transformGPStoCanvas(vehicle.lat, vehicle.lon);
      center.x += vehicle.canvasX ?? transformed.x;
      center.y += vehicle.height ?? 0;  // Для визуализации центра камеры
      center.z += -(vehicle.canvasY ?? transformed.y);
    });
    center.divideScalar(vehicleList.length);
    
    controls.target.copy(center);
    const distance = 100;
    camera.position.set(
      center.x + distance * 0.7,
      center.y + distance * 0.7,
      center.z + distance * 0.7
    );
    controls.update();
    
  };

  // Обработчик изменения камеры (колёсико мыши)
  const handleCameraChange = (distance: number) => {
    // Обновляем дистанцию только если следим за машиной
    if (followingVehicleId) {
      // Увеличиваем диапазон ограничения для более плавной работы камеры
      const newDistance = Math.max(10, Math.min(500, distance));
      
      // Обновляем дистанцию
      setCameraDistance(newDistance);
      
      // Обновление дистанции при зуме колёсиком
    }
  };

  return (
    <div className="three-view-container">
      <header className="three-view-header">
        <h1>3D визуализация Шахты</h1>
        <div className="header-controls">
          <div className="camera-presets">
            <button onClick={() => setCameraView('top')} title="Вид сверху">↓ Сверху</button>
            <button onClick={() => setCameraView('front')} title="Вид спереди">→ Спереди</button>
            <button onClick={() => setCameraView('side')} title="Вид сбоку">← Сбоку</button>
            <button onClick={() => setCameraView('iso')} title="Изометрия">⊡ Изометрия</button>
            <button onClick={() => setCameraView('reset')} title="Сброс">⟲ Сброс</button>
            {/* ✅ ПОСТОЯННЫЕ кнопки зума - работают ВСЕГДА, не только при отслеживании машины */}
            <button 
              onClick={() => {
                if (!controlsRef.current) return;
                const controls = controlsRef.current;
                const camera = controls.object;
                
                // Приближаем камеру к target (уменьшаем distance)
                const direction = new THREE.Vector3();
                direction.subVectors(camera.position, controls.target).normalize();
                const currentDistance = camera.position.distanceTo(controls.target);
                const newDistance = Math.max(10, currentDistance * 0.8);  // Уменьшаем на 20%
                
                camera.position.copy(controls.target).add(direction.multiplyScalar(newDistance));
                controls.update();
                
                // Если следим за машиной - обновляем distance
                if (followingVehicleId) {
                  setCameraDistance(newDistance);
                }
              }} 
              title="Приблизить камеру"
            >
              🔍 Ближе
            </button>
            <button 
              onClick={() => {
                if (!controlsRef.current) return;
                const controls = controlsRef.current;
                const camera = controls.object;
                
                // Отдаляем камеру от target (увеличиваем distance)
                const direction = new THREE.Vector3();
                direction.subVectors(camera.position, controls.target).normalize();
                const currentDistance = camera.position.distanceTo(controls.target);
                const newDistance = Math.min(2000, currentDistance * 1.25);  // Увеличиваем на 25%
                
                camera.position.copy(controls.target).add(direction.multiplyScalar(newDistance));
                controls.update();
                
                // Если следим за машиной - обновляем distance
                if (followingVehicleId) {
                  setCameraDistance(newDistance);
                }
              }} 
              title="Отдалить камеру"
            >
              🔍 Дальше
            </button>
            
            {/* Кнопка отвязки - только когда следим за машиной */}
            {followingVehicleId && (
              <button 
                onClick={() => {
                  setFollowingVehicleId(null);
                }} 
                title="Отвязаться от машины"
              >
                🚫 Отвязка
              </button>
            )}
          </div>
          <button 
            className="back-button"
            onClick={handleBackToEditor}
          >
            ← Редактор
          </button>
        </div>
      </header>

      <div className="three-view-main">
        <div className="three-view-canvas-column">
          {/* Индикатор загрузки сцены */}
          {isLoading && (
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 1000,
              textAlign: 'center',
              color: '#fff',
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              padding: '24px 48px',
              borderRadius: '12px',
              fontSize: '18px',
              fontWeight: 'bold',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)'
            }}>
              ⏳ Загрузка 3D сцены...
            </div>
          )}
          <div className="three-view-canvas" style={{ opacity: isCameraReady ? 1 : 0, transition: 'opacity 0.3s ease-in' }}>
            <Canvas
              camera={{ 
                position: [200, 200, 200],
                fov: 75,
                near: 0.1,
                far: 2000
              }}
              gl={{ 
                antialias: true,
                powerPreference: 'high-performance',
                alpha: true
              }}
            >
              <ThreeScene 
                graphData={allGraphData} 
                vehicles={vehicles} 
                horizons={horizons} 
                controlsRef={controlsRef} 
                selectedHorizon={selectedHorizon} 
                onCameraChange={handleCameraChange} 
                followingVehicleId={followingVehicleId}
                isUserInteractingRef={isUserInteractingRef}
                lastCameraUpdateRef={lastCameraUpdateRef}
                graphCenter={graphCenterState}
                vehicleFirstTeleportPending={vehicleFirstTeleportPending}
                onFirstTeleportDone={(vehicleId) => setVehicleFirstTeleportPending(prev => {
                  const next = new Set(prev);
                  next.delete(vehicleId);
                  return next;
                })}
              />
            </Canvas>
          </div>
        </div>

        <div className="three-view-right-dock">
          <div className="three-view-dock-buttons">
            <button
              type="button"
              className={`three-view-dock-button ${isVehiclePanelOpen ? 'active' : ''}`}
              onClick={() => setIsVehiclePanelOpen((prev) => !prev)}
              title={isVehiclePanelOpen ? 'Скрыть панель транспорта' : 'Показать панель транспорта'}
              aria-pressed={isVehiclePanelOpen}
            >
              <img 
                src="/static/icons/shas_vector.svg" 
                alt="vehicle" 
                style={{
                  width: '23px',
                  height: '23px',
                  objectFit: 'contain'
                }}
              />
              <span className="sr-only">Панель транспорта</span>
            </button>
          </div>

          {isVehiclePanelOpen && (
            <aside className="three-view-side-panel">
              <div className="three-view-panel-shell">
                <div className="three-view-panel-header">
                  <div className="three-view-panel-title-group">
                    <h2 className="three-view-panel-title">Транспорт</h2>
                    <span className="three-view-panel-count">{Object.keys(vehicles).length}</span>
                  </div>
                  <button
                    type="button"
                    className="three-view-panel-toggle"
                    onClick={() => setIsVehiclePanelOpen(false)}
                    title="Скрыть панель"
                  >
                    <span aria-hidden="true">—</span>
                    <span className="sr-only">Скрыть панель</span>
                  </button>
                </div>
                <div className="three-view-panel-body">
                  {Object.keys(vehicles).length > 0 ? (
                    <VehiclePanel
                      vehicles={vehicles}
                      horizons={horizons}
                      onVehicleClick={centerOnVehicle3D}
                      theme="dark"
                      isOpen={isVehiclePanelOpen}
                    />
                  ) : (
                    <div className="three-view-panel-empty">Нет данных о транспорте</div>
                  )}
                </div>
              </div>
            </aside>
          )}
        </div>
      </div>
    </div>
  );
};

export default ThreeView;

