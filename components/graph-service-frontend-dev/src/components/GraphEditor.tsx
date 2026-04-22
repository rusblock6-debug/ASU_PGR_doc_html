/**
 * Компонент для редактирования графа
 */
import React, { useMemo, useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { createNode, createEdge, createPlace, createTag, createHorizon, createLadder, connectLadderNodes, getHorizonObjectsCount, deleteHorizon, getHorizonGraph } from '../services/api';
import { GraphNode, GraphEdge, Tag, Place, VehiclePosition, GraphData, Horizon } from '../types/graph';
import { useSettings, useWebSocket, useGraphData, useVehicles } from '../hooks';
import { EditorToolbar, VehiclesPanel, SettingsPage, ImportDialog, LadderDialog } from './editor';
import { AppHeader } from './shared';
import { getPlaceLonLat, getPlaceMapXY, getPlaceCanvasXY } from '../utils/placeLocation';
import './GraphEditor.css';

const COLOR_ACCENT = '#D15C29';
const COLOR_ACCENT_SOFT = 'rgba(209, 92, 41, 0.18)';
const COLOR_ACCENT_SOFTER = 'rgba(209, 92, 41, 0.10)';
const COLOR_MUTED = '#9F9F9F';
const COLOR_LIGHT = '#FEFCF9';
const COLOR_BG_SURFACE = '#2C2C2C';
const COLOR_CANVAS_BACKGROUND = '#1a1a1a';
const COLOR_GRID_MINOR = 'rgba(254, 252, 249, 0.02)';
const COLOR_GRID_MAJOR = 'rgba(254, 252, 249, 0.05)';
const GRID_BASE_SPACING = 120;

interface GraphEditorProps {
  onVehicleUpdate?: (position: VehiclePosition) => void;
}

const GraphEditor: React.FC<GraphEditorProps> = ({ onVehicleUpdate }) => {
  const navigate = useNavigate();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const ladderIconPositionsRef = useRef<Map<number, {x: number, y: number}>>(new Map());
  
  // Используем кастомные хуки
  const settings = useSettings();
  const graphState = useGraphData();
  
  // Используем централизованный хук для загрузки машин
  const { vehicles: enterpriseVehicles } = useVehicles(1);
  
  const { vehiclePosition, vehicles, clearVehicles } = useWebSocket({
    // НЕ передаем searchHeight - пусть backend использует DEFAULT_VEHICLE_HEIGHT
    onVehicleUpdate,
    vehiclesList: enterpriseVehicles  // Передаём машины для инициализации
  });
  
  // Мапа для хранения названий машин из enterprise-service
  const vehicleNamesMapRef = useRef<Map<string, string>>(new Map());
  
  // Обновляем мапу названий при загрузке машин
  useEffect(() => {
    if (!enterpriseVehicles || enterpriseVehicles.length === 0) return;
    
    const namesMap = new Map<string, string>();
    enterpriseVehicles.forEach(vehicle => {
      // Используем id как ключ
      namesMap.set(String(vehicle.id), vehicle.name);
    });
    vehicleNamesMapRef.current = namesMap;
  }, [enterpriseVehicles]);
  
  // UI состояния
  const [mode, setMode] = useState<'view' | 'addNode' | 'addEdge' | 'addPlace' | 'addLadder' | 'move' | 'edit' | 'delete'>('view');
  const [selectedNode, setSelectedNode] = useState<number | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<number | null>(null);
  const [selectedTag, setSelectedTag] = useState<number | null>(null);
  const [selectedPlace, setSelectedPlace] = useState<number | null>(null);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [previousHorizonId, setPreviousHorizonId] = useState<number | null>(null); // Отслеживание смены уровня
  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const [showEditTag, setShowEditTag] = useState(false);
  const [editingPlace, setEditingPlace] = useState<Place | null>(null);
  const [showEditPlace, setShowEditPlace] = useState(false);
  const [editingNode, setEditingNode] = useState<GraphNode | null>(null);
  const [showEditNode, setShowEditNode] = useState(false);
  const [editingEdge, setEditingEdge] = useState<GraphEdge | null>(null);
  const [showEditEdge, setShowEditEdge] = useState(false);
  const [editingLadderNode, setEditingLadderNode] = useState<GraphNode | null>(null);
  const [showEditLadder, setShowEditLadder] = useState(false);
  const [ladderConnectedNodes, setLadderConnectedNodes] = useState<Array<{node: GraphNode, edge: GraphEdge, horizon: Horizon}>>([]);
  const [loadingLadderConnections, setLoadingLadderConnections] = useState(false);
  const [isDraggingRadius, setIsDraggingRadius] = useState(false);
  const [draggingTagId, setDraggingTagId] = useState<number | null>(null);
  const [tempRadius, setTempRadius] = useState<number | null>(null);
  const [isLeftPanelOpen, setIsLeftPanelOpen] = useState(false);
  const [isVehiclesPanelOpen, setIsVehiclesPanelOpen] = useState(false);
  const [currentView, setCurrentView] = useState<'settings' | 'graphs' | 'editor' | 'viewer'>('editor');
  const [showCoordinates, setShowCoordinates] = useState(false);
  const [cursorPos, setCursorPos] = useState<{x: number, y: number} | null>(null);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [showLadderDialog, setShowLadderDialog] = useState(false);
  const [ladderSourceNode, setLadderSourceNode] = useState<GraphNode | null>(null);
  const [ladderLevel1Id, setLadderLevel1Id] = useState<number | null>(null);
  const [ladderLevel2Id, setLadderLevel2Id] = useState<number | null>(null);
  const [ladderNode1Id, setLadderNode1Id] = useState<number | null>(null);
  const [ladderNode2Id, setLadderNode2Id] = useState<number | null>(null);
  const [ladderStep, setLadderStep] = useState<'selectLevels' | 'selectNode1' | 'selectNode2' | null>(null);
  const [leftDockSelection, setLeftDockSelection] = useState<'horizons' | 'tools' | null>(null);
  
  // Состояния для перемещения объектов
  const [isDraggingObject, setIsDraggingObject] = useState(false);
  const [draggingObjectType, setDraggingObjectType] = useState<'node' | 'tag' | null>(null);
  const [draggingObjectId, setDraggingObjectId] = useState<number | null>(null);
  const [dragStartPos, setDragStartPos] = useState<{x: number, y: number} | null>(null);
  
  const [dragCurrentPos, setDragCurrentPos] = useState<{x: number, y: number} | null>(null);

  const PANEL_WIDTH = 220;

  const leftPanelStyle: React.CSSProperties = {
    width: PANEL_WIDTH
  };

  const rightPanelStyle: React.CSSProperties = {
    width: PANEL_WIDTH,
    transform: isVehiclesPanelOpen
      ? 'translateX(0)'
      : `translateX(${PANEL_WIDTH}px)`
  };

  const selectionPanelStyle: React.CSSProperties = {
    right: 32,
  };
  const hasSelection = Boolean(selectedNode || selectedEdge || selectedTag || selectedPlace);

  // Состояния для panning canvas
  const [isPanning, setIsPanning] = useState(false);
  const [panStartPos, setPanStartPos] = useState<{x: number, y: number} | null>(null);
  
  // Состояния для ошибок валидации
  const [nodeError, setNodeError] = useState<string | null>(null);
  const [edgeError, setEdgeError] = useState<string | null>(null);
  const [tagError, setTagError] = useState<string | null>(null);
  const [placeError, setPlaceError] = useState<string | null>(null);

  // Радиусы для places берём из связанного тэга (telemetry): tag.place_id -> max(tag.radius)
  const placeRadiusMap = useMemo(() => {
    const m = new Map<number, number>();
    const tags = graphState.graphData?.tags ?? [];
    tags.forEach((t) => {
      if (!t.place_id) return;
      const r = t.radius || 25;
      const prev = m.get(t.place_id) ?? 0;
      m.set(t.place_id, Math.max(prev, r));
    });
    return m;
  }, [graphState.graphData?.tags]);

  // WebSocket и загрузка данных теперь обрабатываются через хуки
  // useSettings, useWebSocket, useGraphData

  // КРИТИЧЕСКИЙ FIX: Принудительный сброс старой координатной калибровации
  useEffect(() => {
    const storedCalibration = localStorage.getItem('coordinateCalibration');
    if (storedCalibration) {
      try {
        const parsed = JSON.parse(storedCalibration);
        if (parsed.enabled === true) {
          localStorage.removeItem('coordinateCalibration');
          window.location.reload();
          return;
        }
      } catch (e) {
        console.error('Ошибка парсинга coordinateCalibration:', e);
      }
    }
  }, []);

  // Отрисовка графа
  useEffect(() => {
    if (canvasRef.current) {
      drawGraph();
    }
  }, [graphState.graphData, vehiclePosition, scale, offset, dragCurrentPos, isDraggingObject, draggingObjectId, selectedNode, selectedTag, selectedPlace]);
  
  // Non-passive event listeners для предотвращения скролла и обработки zoom
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    // Обработчик wheel события с preventDefault и zoom
    const handleWheelEvent = (e: WheelEvent) => {
      e.preventDefault();
      // Обработка zoom
      handleZoom(e.deltaY > 0 ? -0.1 : 0.1);
    };
    
    // Предотвращение scroll для touch событий
    const preventScroll = (e: Event) => {
      e.preventDefault();
    };
    
    // Добавляем non-passive event listeners
    canvas.addEventListener('touchstart', preventScroll, { passive: false });
    canvas.addEventListener('touchmove', preventScroll, { passive: false });
    canvas.addEventListener('touchend', preventScroll, { passive: false });
    canvas.addEventListener('wheel', handleWheelEvent, { passive: false });
    
    return () => {
      canvas.removeEventListener('touchstart', preventScroll);
      canvas.removeEventListener('touchmove', preventScroll);
      canvas.removeEventListener('touchend', preventScroll);
      canvas.removeEventListener('wheel', handleWheelEvent);
    };
  }, []); // Без зависимостей - регистрируем один раз

  // Функции loadHorizons и loadGraphData теперь в хуке useGraphData

  // Функция для создания пути сердцевины метки в зависимости от типа (без fill/stroke)
  const createTagCenterPath = (ctx: CanvasRenderingContext2D, x: number, y: number, size: number, tagType: string) => {
    ctx.beginPath();
    
    switch (tagType) {
      case 'transit':
        // Кружок
        ctx.arc(x, y, size, 0, 2 * Math.PI);
        break;
      case 'loading':
        // Треугольник
        ctx.moveTo(x, y - size);
        ctx.lineTo(x - size * 0.866, y + size * 0.5);
        ctx.lineTo(x + size * 0.866, y + size * 0.5);
        ctx.closePath();
        break;
      case 'transfer':
        // Квадрат
        ctx.rect(x - size, y - size, size * 2, size * 2);
        break;
      case 'unloading':
        // Звездочка (5-конечная)
        const spikes = 5;
        const outerRadius = size;
        const innerRadius = size * 0.5;
        for (let i = 0; i < spikes * 2; i++) {
          const radius = i % 2 === 0 ? outerRadius : innerRadius;
          const angle = (Math.PI * i) / spikes - Math.PI / 2;
          const px = x + Math.cos(angle) * radius;
          const py = y + Math.sin(angle) * radius;
          if (i === 0) {
            ctx.moveTo(px, py);
          } else {
            ctx.lineTo(px, py);
          }
        }
        ctx.closePath();
        break;
      case 'transport':
        // Пятиугольник
        const sides = 5;
        for (let i = 0; i < sides; i++) {
          const angle = (Math.PI * 2 * i) / sides - Math.PI / 2;
          const px = x + Math.cos(angle) * size;
          const py = y + Math.sin(angle) * size;
          if (i === 0) {
            ctx.moveTo(px, py);
          } else {
            ctx.lineTo(px, py);
          }
        }
        ctx.closePath();
        break;
      default:
        // По умолчанию кружок
        ctx.arc(x, y, size, 0, 2 * Math.PI);
    }
  };

  const drawGraph = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Размеры холста
    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;

    // Всегда очищаем canvas перед дальнейшей логикой, чтобы не оставалось артефактов
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);

    // Заполняем глубоким фоном
    ctx.fillStyle = COLOR_CANVAS_BACKGROUND;
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    // Границы видимой области в "мировых" координатах (до трансформации)
    const worldLeft = -offset.x / scale;
    const worldTop = -offset.y / scale;
    const worldRight = worldLeft + canvasWidth / scale;
    const worldBottom = worldTop + canvasHeight / scale;

    // Рассчитываем адаптивный шаг сетки, чтобы линии оставались комфортными при любом масштабе
    let gridSpacing = GRID_BASE_SPACING;
    let pixelSpacing = gridSpacing * scale;
    while (pixelSpacing < 60) {
      gridSpacing *= 2;
      pixelSpacing = gridSpacing * scale;
    }
    while (pixelSpacing > 240 && gridSpacing > GRID_BASE_SPACING / 4) {
      gridSpacing /= 2;
      pixelSpacing = gridSpacing * scale;
    }

    ctx.save();
    ctx.translate(offset.x, offset.y);
    ctx.scale(scale, scale);

    // Рисуем "анимус" сетку
    const firstVertical = Math.floor(worldLeft / gridSpacing) * gridSpacing;
    const firstHorizontal = Math.floor(worldTop / gridSpacing) * gridSpacing;

    for (let x = firstVertical; x <= worldRight + gridSpacing; x += gridSpacing) {
      const gridIndex = Math.round(x / gridSpacing);
      const isMajor = gridIndex % 5 === 0;
      ctx.beginPath();
      ctx.strokeStyle = isMajor ? COLOR_GRID_MAJOR : COLOR_GRID_MINOR;
      ctx.lineWidth = (isMajor ? 1.6 : 0.9) / scale;
      ctx.moveTo(x, worldTop - gridSpacing);
      ctx.lineTo(x, worldBottom + gridSpacing);
      ctx.stroke();
    }

    for (let y = firstHorizontal; y <= worldBottom + gridSpacing; y += gridSpacing) {
      const gridIndex = Math.round(y / gridSpacing);
      const isMajor = gridIndex % 5 === 0;
      ctx.beginPath();
      ctx.strokeStyle = isMajor ? COLOR_GRID_MAJOR : COLOR_GRID_MINOR;
      ctx.lineWidth = (isMajor ? 1.6 : 0.9) / scale;
      ctx.moveTo(worldLeft - gridSpacing, y);
      ctx.lineTo(worldRight + gridSpacing, y);
      ctx.stroke();
    }

    if (!graphState.graphData) {
      ctx.restore();
      return;
    }

    // Локальная ссылка для TypeScript (non-null после проверки)
    const graphData = graphState.graphData!;

    // Применение трансформации
    // Контекст уже находится в нужной системе координат после сетки

    // Отрисовка ребер
    ctx.strokeStyle = COLOR_MUTED;
    ctx.lineWidth = 1.2;
    graphData.edges.forEach(edge => {
      const fromNode = graphData.nodes.find(n => n.id === edge.from_node_id);
      const toNode = graphData.nodes.find(n => n.id === edge.to_node_id);
      
      if (fromNode && toNode) {
        // ✅ Преобразуем GPS координаты в canvas координаты
        const fromCanvasPos = settings.transformGPStoCanvas(fromNode.y, fromNode.x);
        const toCanvasPos = settings.transformGPStoCanvas(toNode.y, toNode.x);
        
        // Используем временные позиции если узлы перемещаются
        const fromX = (isDraggingObject && draggingObjectType === 'node' && draggingObjectId === fromNode.id && dragCurrentPos)
          ? dragCurrentPos.x
          : fromCanvasPos.x;
        const fromY = (isDraggingObject && draggingObjectType === 'node' && draggingObjectId === fromNode.id && dragCurrentPos)
          ? dragCurrentPos.y
          : fromCanvasPos.y;
        const toX = (isDraggingObject && draggingObjectType === 'node' && draggingObjectId === toNode.id && dragCurrentPos)
          ? dragCurrentPos.x
          : toCanvasPos.x;
        const toY = (isDraggingObject && draggingObjectType === 'node' && draggingObjectId === toNode.id && dragCurrentPos)
          ? dragCurrentPos.y
          : toCanvasPos.y;
        
        ctx.beginPath();
        ctx.moveTo(fromX, fromY);
        ctx.lineTo(toX, toY);
        ctx.stroke();
      }
    });

    // Очищаем позиции иконок лестниц перед отрисовкой
    ladderIconPositionsRef.current.clear();
    
    // Отрисовка узлов
    graphState.graphData.nodes.forEach(node => {
      const isSelected = selectedNode === node.id;
      const isLadderNode1 = ladderNode1Id === node.id;
      const isLadderNode2 = ladderNode2Id === node.id;
      
      // Проверяем, есть ли у узла лестница (вертикальное соединение)
      const hasLadder = node.node_type === 'ladder' || 
        (graphState.graphData?.edges?.some(edge => 
          (edge.from_node_id === node.id || edge.to_node_id === node.id) && 
          edge.edge_type === 'vertical'
        ) ?? false);
      
      // ✅ Преобразуем GPS координаты в canvas координаты
      const canvasPos = settings.transformGPStoCanvas(node.y, node.x);  // lat, lon
      
      // Используем временную позицию если объект перемещается
      const nodeX = (isDraggingObject && draggingObjectType === 'node' && draggingObjectId === node.id && dragCurrentPos)
        ? dragCurrentPos.x
        : canvasPos.x;
      const nodeY = (isDraggingObject && draggingObjectType === 'node' && draggingObjectId === node.id && dragCurrentPos)
        ? dragCurrentPos.y
        : canvasPos.y;
      
      // Подсветка выбранного узла с glow эффектом
      if (isSelected) {
        ctx.shadowColor = COLOR_ACCENT;
        ctx.shadowBlur = 12;
        ctx.strokeStyle = COLOR_ACCENT;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(nodeX, nodeY, 8, 0, 2 * Math.PI);
        ctx.stroke();
        ctx.shadowBlur = 0;
      }
      
      // Визуальная индикация узлов при создании лестницы
      if (mode === 'addLadder' && ladderStep !== null) {
        if (isLadderNode1) {
          // Первый выбранный узел - зеленый
          ctx.shadowColor = '#2ecc71';
          ctx.shadowBlur = 15;
          ctx.strokeStyle = '#2ecc71';
          ctx.lineWidth = 4;
          ctx.beginPath();
          ctx.arc(nodeX, nodeY, 10, 0, 2 * Math.PI);
          ctx.stroke();
          ctx.shadowBlur = 0;
          
          // Подпись "Узел 1"
          ctx.fillStyle = '#2ecc71';
          ctx.font = 'bold 12px Arial';
          ctx.textAlign = 'center';
          ctx.fillText('Узел 1', nodeX, nodeY - 18);
        } else if (isLadderNode2) {
          // Второй выбранный узел - синий
          ctx.shadowColor = '#3498db';
          ctx.shadowBlur = 15;
          ctx.strokeStyle = '#3498db';
          ctx.lineWidth = 4;
          ctx.beginPath();
          ctx.arc(nodeX, nodeY, 10, 0, 2 * Math.PI);
          ctx.stroke();
          ctx.shadowBlur = 0;
          
          // Подпись "Узел 2"
          ctx.fillStyle = '#3498db';
          ctx.font = 'bold 12px Arial';
          ctx.textAlign = 'center';
          ctx.fillText('Узел 2', nodeX, nodeY - 18);
        } else if (ladderStep === 'selectNode1' && node.horizon_id === ladderLevel1Id) {
          // Подсветка узлов на первом уровне при выборе первого узла
          ctx.strokeStyle = 'rgba(46, 204, 113, 0.5)';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(nodeX, nodeY, 7, 0, 2 * Math.PI);
          ctx.stroke();
        } else if (ladderStep === 'selectNode2' && node.horizon_id === ladderLevel2Id) {
          // Подсветка узлов на втором уровне при выборе второго узла
          ctx.strokeStyle = 'rgba(52, 152, 219, 0.5)';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(nodeX, nodeY, 7, 0, 2 * Math.PI);
          ctx.stroke();
        }
      }
      
      const baseRadius = 5;
      ctx.fillStyle = '#9F9F9F'; // Зеленый цвет для всех узлов
      ctx.beginPath();
      ctx.arc(nodeX, nodeY, baseRadius, 0, 2 * Math.PI);
      ctx.fill();
      
      // Дополнительное выделение
      if (isSelected) {
        ctx.strokeStyle = COLOR_LIGHT;
        ctx.lineWidth = 1.8;
        ctx.stroke();
      }
      
      // Отрисовка значка пружинки для узлов с лестницей
      if (hasLadder && currentView === 'editor') {
        const iconY = nodeY + 20; // Располагаем ниже узла
        const iconRadius = 12;
        
        // Сохраняем позицию иконки для обработки кликов (используем ref)
        ladderIconPositionsRef.current.set(node.id, { x: nodeX, y: iconY });
        
        // Фон для значка (круглый фон) - фиолетовый цвет
        ctx.fillStyle = 'rgba(138, 43, 226, 0.95)'; // Фиолетовый цвет
        ctx.beginPath();
        ctx.arc(nodeX, iconY, iconRadius, 0, 2 * Math.PI);
        ctx.fill();
        
        // Обводка для лучшей видимости
        ctx.strokeStyle = COLOR_LIGHT;
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // Значок пружинки (🪜)
        ctx.fillStyle = COLOR_LIGHT;
        ctx.font = 'bold 16px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('🪜', nodeX, iconY);
      }
    });

    // Подсветка выбранного ребра
    if (selectedEdge) {
      const edge = graphState.graphData.edges.find(e => e.id === selectedEdge);
      if (edge) {
        const fromNode = graphState.graphData.nodes.find(n => n.id === edge.from_node_id);
        const toNode = graphState.graphData.nodes.find(n => n.id === edge.to_node_id);
        if (fromNode && toNode) {
          ctx.strokeStyle = COLOR_ACCENT;
          ctx.lineWidth = 4;
          ctx.beginPath();
          ctx.moveTo(fromNode.x, fromNode.y);
          ctx.lineTo(toNode.x, toNode.y);
          ctx.stroke();
        }
      }
    }

    // Отрисовка точек на карте:
    // - новый источник координат: graphData.places (preferred)
    // - fallback: tags (для старых данных), если places пустой
    const mapPlaces = Array.isArray(graphData.places) && graphData.places.length > 0 ? graphData.places : null;

    const normalizePlaceType = (t: string): string => {
      // унифицируем типы places под старые формы/иконки
      switch ((t || '').toLowerCase()) {
        case 'load':
        case 'loading':
          return 'loading';
        case 'reload':
        case 'transfer':
          return 'transfer';
        case 'unload':
        case 'unloading':
          return 'unloading';
        case 'park':
        case 'transport':
          return 'transport';
        case 'transit':
        default:
          return 'transit';
      }
    };

    if (mapPlaces) {
      mapPlaces.forEach((place) => {
        const canvasPos = getPlaceCanvasXY(place, settings.transformGPStoCanvas);
        if (!canvasPos) return;

        const isSelectedPlace = selectedPlace === place.id;
        if (isSelectedPlace) {
          ctx.shadowColor = COLOR_ACCENT;
          ctx.shadowBlur = 18;
          ctx.strokeStyle = COLOR_ACCENT;
          ctx.lineWidth = 3 / scale;
          ctx.beginPath();
          ctx.arc(canvasPos.x, canvasPos.y, 10, 0, 2 * Math.PI);
          ctx.stroke();
          ctx.shadowBlur = 0;
        }

        // Радиус места из связанного тэга
        const placeRadius = placeRadiusMap.get(place.id);
        if (placeRadius && placeRadius > 0) {
          ctx.fillStyle = COLOR_ACCENT_SOFTER;
          ctx.strokeStyle = COLOR_ACCENT;
          ctx.lineWidth = 1.4 / scale;
          ctx.beginPath();
          ctx.arc(canvasPos.x, canvasPos.y, placeRadius, 0, 2 * Math.PI);
          ctx.fill();
          ctx.stroke();
        }

        // Точка места (без радиуса)
        ctx.fillStyle = COLOR_ACCENT;
        ctx.strokeStyle = COLOR_LIGHT;
        ctx.lineWidth = 1.2 / scale;

        const size = 4.2;
        createTagCenterPath(ctx, canvasPos.x, canvasPos.y, size, normalizePlaceType(place.type));
        ctx.fill();
        ctx.stroke();

        // Подпись
        ctx.fillStyle = COLOR_LIGHT;
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(place.name, canvasPos.x, canvasPos.y - 10);
      });
    } else {
      graphData.tags.forEach(tag => {
        const isSelected = selectedTag === tag.id;
        const currentRadius = isDraggingRadius && draggingTagId === tag.id && tempRadius !== null
          ? tempRadius
          : tag.radius || 25;

        // ✅ Fallback координаты: сначала из tag.place.location, иначе из tag.x/tag.y
        const lonLatFromPlace = tag.place ? getPlaceLonLat(tag.place) : null;
        const gpsLat: number = lonLatFromPlace?.lat ?? (tag.y ?? 0);
        const gpsLon: number = lonLatFromPlace?.lon ?? (tag.x ?? 0);
        const tagCanvasPos = settings.transformGPStoCanvas(gpsLat, gpsLon);

        // Используем временную позицию если метка перемещается
        const tagX = (isDraggingObject && draggingObjectType === 'tag' && draggingObjectId === tag.id && dragCurrentPos)
          ? dragCurrentPos.x
          : tagCanvasPos.x;
        const tagY = (isDraggingObject && draggingObjectType === 'tag' && draggingObjectId === tag.id && dragCurrentPos)
          ? dragCurrentPos.y
          : tagCanvasPos.y;

        // Подсветка выбранной метки с glow эффектом
        if (isSelected) {
          ctx.shadowColor = COLOR_ACCENT;
          ctx.shadowBlur = 20;
        }

        ctx.fillStyle = isSelected ? COLOR_ACCENT_SOFT : COLOR_ACCENT_SOFTER;
        ctx.strokeStyle = COLOR_ACCENT;
        ctx.lineWidth = isSelected ? 3 : 1.6;

        // Зона действия метки
        ctx.beginPath();
        ctx.arc(tagX, tagY, currentRadius, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Центр метки - разные формы в зависимости от типа
        ctx.fillStyle = COLOR_ACCENT;
        const centerSize = isSelected ? 5 : 3.5;

        // Создаем путь для сердцевины метки
        createTagCenterPath(ctx, tagX, tagY, centerSize, tag.point_type || 'transit');
        ctx.fill();

        // Белая обводка для выделения
        if (isSelected) {
          ctx.strokeStyle = COLOR_LIGHT;
          ctx.lineWidth = 2;
          // Пересоздаем путь для обводки
          createTagCenterPath(ctx, tagX, tagY, centerSize, tag.point_type || 'transit');
          ctx.stroke();
        }

        // Название метки
        ctx.fillStyle = COLOR_LIGHT;
        ctx.font = isSelected ? 'bold 14px Arial' : '12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(tag.name || tag.beacon_id || tag.tag_id || 'Tag', tagX, tagY - (currentRadius + 10));

        // Drag handle для изменения радиуса (только для выбранной метки в режиме view или edit)
        if (isSelected && (mode === 'view' || mode === 'edit')) {
          // Четыре handles по сторонам света
          const handlePositions = [
            { x: tagX + currentRadius, y: tagY },      // Восток
            { x: tagX, y: tagY + currentRadius },      // Юг
            { x: tagX - currentRadius, y: tagY },      // Запад
            { x: tagX, y: tagY - currentRadius }       // Север
          ];

          handlePositions.forEach(pos => {
            // Внешний круг handle
            ctx.fillStyle = COLOR_LIGHT;
            ctx.strokeStyle = COLOR_LIGHT;
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, 6, 0, 2 * Math.PI);
            ctx.fill();
            ctx.stroke();

            // Внутренний кружок для визуального эффекта
            ctx.fillStyle = COLOR_LIGHT;
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, 3, 0, 2 * Math.PI);
            ctx.fill();
          });
        }
      });
    }

    // Отрисовка ВСЕХ транспортных средств
    if (vehicles && Object.keys(vehicles).length > 0 && graphState.selectedHorizon) {
      const currentHorizon = graphState.selectedHorizon; // Сохраняем в константу для TypeScript
      
      Object.values(vehicles).forEach(vehicle => {
        // Используем height из данных (если нет - не показываем машину)
        const vehicleHeight = vehicle.height;
        if (vehicleHeight === undefined || vehicleHeight === null) {
          // Высота не известна - не показываем машину в режиме редактирования
          return;
        }
        
        // Проверяем что транспорт на текущем уровне (допуск ±5 метров)
        const vehicleOnCurrentHorizon = Math.abs(vehicleHeight - currentHorizon.height) < 5;
        
        if (vehicleOnCurrentHorizon) {
          // Трансформируем GPS координаты в Canvas координаты
          const canvasPos = settings.transformGPStoCanvas(vehicle.lat, vehicle.lon);
          
          const triangleSize = 26;
          const halfBase = triangleSize * 0.6;
          const height = triangleSize;

          ctx.beginPath();
          ctx.fillStyle = '#2ecc71';
          ctx.beginPath();
          ctx.moveTo(canvasPos.x, canvasPos.y); // острие указывает на текущую координату
          ctx.lineTo(canvasPos.x - halfBase, canvasPos.y - height);
          ctx.lineTo(canvasPos.x + halfBase, canvasPos.y - height);
          ctx.closePath();
          ctx.fill();

          ctx.strokeStyle = '#0c0c0c';
          ctx.lineWidth = 2;
          ctx.stroke();
          
          // Получаем название машины из мапы или используем vehicle_id
          const vehicleName = vehicleNamesMapRef.current.get(vehicle.vehicle_id);
          const label = vehicleName || vehicle.name || vehicle.vehicle_id;
          ctx.font = 'bold 12px Arial';
          ctx.textAlign = 'center';
          const textX = canvasPos.x;
          const textY = canvasPos.y - triangleSize * 1.2;
          const metrics = ctx.measureText(label);
          const paddingX = 6;
          const paddingY = 4;
          const labelWidth = metrics.width + paddingX * 2;
          const labelHeight = 14 + paddingY * 2;

          ctx.fillStyle = 'rgba(17, 17, 17, 0.85)';
          ctx.beginPath();
          if (typeof ctx.roundRect === 'function') {
            ctx.roundRect(
              textX - labelWidth / 2,
              textY - labelHeight + paddingY,
              labelWidth,
              labelHeight,
              6
            );
          } else {
            const r = 6;
            const bx = textX - labelWidth / 2;
            const by = textY - labelHeight + paddingY;
            const bw = labelWidth;
            const bh = labelHeight;
            ctx.moveTo(bx + r, by);
            ctx.lineTo(bx + bw - r, by);
            ctx.quadraticCurveTo(bx + bw, by, bx + bw, by + r);
            ctx.lineTo(bx + bw, by + bh - r);
            ctx.quadraticCurveTo(bx + bw, by + bh, bx + bw - r, by + bh);
            ctx.lineTo(bx + r, by + bh);
            ctx.quadraticCurveTo(bx, by + bh, bx, by + bh - r);
            ctx.lineTo(bx, by + r);
            ctx.quadraticCurveTo(bx, by, bx + r, by);
            ctx.closePath();
          }
          ctx.fill();

          ctx.fillStyle = COLOR_LIGHT;
          ctx.fillText(label, textX, textY);
        }
      });
    }

    ctx.restore();
  };

  const getCanvasPoint = (canvas: HTMLCanvasElement, clientX: number, clientY: number) => {
    const rect = canvas.getBoundingClientRect();
    const scaleX = rect.width ? canvas.width / rect.width : 1;
    const scaleY = rect.height ? canvas.height / rect.height : 1;
    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY,
    };
  };

  const handleMouseDown = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || !graphState.graphData) return;

    const hasPlaces = Array.isArray(graphState.graphData.places) && graphState.graphData.places.length > 0;
    const { x: rawX, y: rawY } = getCanvasPoint(canvas, event.clientX, event.clientY);
    const x = (rawX - offset.x) / scale;
    const y = (rawY - offset.y) / scale;

    // Проверка, клик был на handle для изменения радиуса
    if (!hasPlaces && selectedTag && (mode === 'view' || mode === 'edit')) {
      const tag = graphState.graphData.tags.find(t => t.id === selectedTag);
      if (tag) {
        const lonLatFromPlace = tag.place ? getPlaceLonLat(tag.place) : null;
        const gpsLat: number = lonLatFromPlace?.lat ?? (tag.y ?? 0);
        const gpsLon: number = lonLatFromPlace?.lon ?? (tag.x ?? 0);
        const tagCanvasPos = settings.transformGPStoCanvas(gpsLat, gpsLon);
        const handlePositions = [
          { x: tagCanvasPos.x + (tag.radius || 25), y: tagCanvasPos.y },
          { x: tagCanvasPos.x, y: tagCanvasPos.y + (tag.radius || 25) },
          { x: tagCanvasPos.x - (tag.radius || 25), y: tagCanvasPos.y },
          { x: tagCanvasPos.x, y: tagCanvasPos.y - (tag.radius || 25) }
        ];
        
        for (const pos of handlePositions) {
          const distance = Math.sqrt((pos.x - x) ** 2 + (pos.y - y) ** 2);
          if (distance < 10) {
            setIsDraggingRadius(true);
            setDraggingTagId(tag.id);
            setTempRadius(tag.radius || 25);
            event.preventDefault();
            return;
          }
        }
      }
    }

    // Режим перемещения объектов
    if (mode === 'move') {
      // Проверка клика по узлу
      for (const node of graphState.graphData.nodes) {
        // ✅ Преобразуем GPS координаты в canvas координаты
        const nodeCanvasPos = settings.transformGPStoCanvas(node.y, node.x);
        const distance = Math.sqrt((nodeCanvasPos.x - x) ** 2 + (nodeCanvasPos.y - y) ** 2);
        if (distance < 10) {
          setIsDraggingObject(true);
          setDraggingObjectType('node');
          setDraggingObjectId(node.id);
          setDragStartPos({ x: nodeCanvasPos.x, y: nodeCanvasPos.y });
          setDragCurrentPos({ x: nodeCanvasPos.x, y: nodeCanvasPos.y });
          // В режиме перемещения не устанавливаем selectedNode, чтобы не открывался попап
          event.preventDefault();
          return;
        }
      }
      
      // Проверка клика по метке
      if (!hasPlaces) for (const tag of graphState.graphData.tags) {
        const lonLatFromPlace = tag.place ? getPlaceLonLat(tag.place) : null;
        const gpsLat: number = lonLatFromPlace?.lat ?? (tag.y ?? 0);
        const gpsLon: number = lonLatFromPlace?.lon ?? (tag.x ?? 0);
        const tagCanvasPos = settings.transformGPStoCanvas(gpsLat, gpsLon);
        const distance = Math.sqrt((tagCanvasPos.x - x) ** 2 + (tagCanvasPos.y - y) ** 2);
        if (distance < (tag.radius || 25)) {
          setIsDraggingObject(true);
          setDraggingObjectType('tag');
          setDraggingObjectId(tag.id);
          setDragStartPos({ x: tagCanvasPos.x, y: tagCanvasPos.y });
          setDragCurrentPos({ x: tagCanvasPos.x, y: tagCanvasPos.y });
          // В режиме перемещения не устанавливаем selectedTag, чтобы не открывался попап
          event.preventDefault();
          return;
        }
      }
      
      // Если не попали ни по одному объекту - начинаем panning canvas
      setIsPanning(true);
      setPanStartPos({ 
        x: rawX - offset.x, 
        y: rawY - offset.y 
      });
      event.preventDefault();
      return;
    }
    
  };
  

  const handleMouseMove = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const { x: rawX, y: rawY } = getCanvasPoint(canvas, event.clientX, event.clientY);
    const x = (rawX - offset.x) / scale;
    const y = (rawY - offset.y) / scale;

    // Обновляем позицию курсора для показа координат
    setCursorPos({ x, y });

    // Panning canvas
    if (isPanning && panStartPos) {
      const newOffsetX = rawX - panStartPos.x;
      const newOffsetY = rawY - panStartPos.y;
      setOffset({ x: newOffsetX, y: newOffsetY });
      return;
    }

    // Изменение радиуса legacy-метки (только если places пустой)
    if (
      isDraggingRadius &&
      draggingTagId &&
      graphState.graphData &&
      !(Array.isArray(graphState.graphData.places) && graphState.graphData.places.length > 0)
    ) {
      const tag = graphState.graphData.tags.find(t => t.id === draggingTagId);
      if (tag) {
        const lonLatFromPlace = tag.place ? getPlaceLonLat(tag.place) : null;
        const gpsLat: number = lonLatFromPlace?.lat ?? (tag.y ?? 0);
        const gpsLon: number = lonLatFromPlace?.lon ?? (tag.x ?? 0);
        const tagCanvasPos = settings.transformGPStoCanvas(gpsLat, gpsLon);
        const distance = Math.sqrt((x - tagCanvasPos.x) ** 2 + (y - tagCanvasPos.y) ** 2);
        const newRadius = Math.max(10, Math.min(100, distance)); // Ограничение радиуса 10-100
        setTempRadius(newRadius);
      }
      return;
    }

    // Перемещение объекта
    if (isDraggingObject && draggingObjectId) {
      setDragCurrentPos({ x, y });
    }
  };

  const handleMouseUp = async () => {
    // Завершение panning canvas
    if (isPanning) {
      setIsPanning(false);
      setPanStartPos(null);
      return;
    }
    
    // Сохранение нового радиуса метки
    if (isDraggingRadius && draggingTagId !== null && tempRadius !== null) {
      try {
        const tag = graphState.graphData?.tags.find(t => t.id === draggingTagId);
        if (tag) {
          const response = await fetch(`/api/tags/${draggingTagId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ radius: tempRadius })
          });
          if (!response.ok) {
            const raw = await response.text();
            let errorData: any = raw;
            try { errorData = JSON.parse(raw); } catch { /* keep raw */ }
            console.error('Failed to update tag radius:', response.status, errorData);
            throw new Error(`Failed to update tag radius: ${typeof errorData === 'string' ? errorData : JSON.stringify(errorData)}`);
          }
          
          // Обновляем граф (fitGraphToCanvas не вызовется, т.к. уровень не изменился)
          if (graphState.selectedHorizon) {
            graphState.loadGraphData(graphState.selectedHorizon.id);
          }
        }
      } catch (error) {
        console.error('Error updating tag radius:', error);
      }
      
      setIsDraggingRadius(false);
      setDraggingTagId(null);
      setTempRadius(null);
      return;
    }

    // Сохранение новой позиции объекта
    if (isDraggingObject && draggingObjectId && dragCurrentPos && dragStartPos) {
      try {
        if (draggingObjectType === 'node') {
          const node = graphState.graphData?.nodes.find(n => n.id === draggingObjectId);
          if (node) {
            // ✅ Преобразуем canvas координаты обратно в GPS перед сохранением
            const gpsCoords = settings.transformCanvasToGPS(dragCurrentPos.x, dragCurrentPos.y);
            const response = await fetch(`/api/nodes/${draggingObjectId}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ 
                x: gpsCoords.lon,  // ✅ GPS longitude
                y: gpsCoords.lat   // ✅ GPS latitude
                // z не отправляем - это readonly поле, вычисляется из horizon.height
              })
            });
            
            if (!response.ok) {
              const raw = await response.text();
              let errorData: any = raw;
              try { errorData = JSON.parse(raw); } catch { /* leave raw */ }
              console.error('Failed to update node:', response.status, errorData);
              throw new Error(`Failed to update node: ${typeof errorData === 'string' ? errorData : JSON.stringify(errorData)}`);
            }
          }
        } else if (draggingObjectType === 'tag') {
          const tag = graphState.graphData?.tags.find(t => t.id === draggingObjectId);
          if (tag && tag.place_id) {
            // ✅ Преобразуем canvas координаты обратно в GPS перед сохранением
            const gpsCoords = settings.transformCanvasToGPS(dragCurrentPos.x, dragCurrentPos.y);
            // Обновляем Place (координаты теперь там, не в Tag)
            const response = await fetch(`/api/places/${tag.place_id}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ 
                location: {
                  x: dragCurrentPos.x,  // Canvas координаты
                  y: dragCurrentPos.y,
                  lat: gpsCoords.lat,   // GPS координаты
                  lon: gpsCoords.lon
                }
              })
            });
            
            if (!response.ok) {
              const raw = await response.text();
              let errorData: any = raw;
              try { errorData = JSON.parse(raw); } catch { /* leave raw */ }
              console.error('Failed to update place location:', response.status, errorData);
              throw new Error(`Failed to update place location: ${typeof errorData === 'string' ? errorData : JSON.stringify(errorData)}`);
            }
          }
        }
        
        // Обновляем граф (fitGraphToCanvas не вызовется, т.к. уровень не изменился)
        if (graphState.selectedHorizon) {
          graphState.loadGraphData(graphState.selectedHorizon.id);
        }
      } catch (error) {
        console.error('Error updating object position:', error);
      }
    }
    
    setIsDraggingObject(false);
    setDraggingObjectType(null);
    setDraggingObjectId(null);
    setDragStartPos(null);
    setDragCurrentPos(null);
  };

  const handleMouseUpOutside = () => {
    if (isPanning) {
      setIsPanning(false);
      setPanStartPos(null);
    }
  };

  const handleMouseLeave = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (isPanning) {
      setIsPanning(false);
      setPanStartPos(null);
    }
    if (showCoordinates) {
      setCursorPos(null);
    }
  };

  const handleCanvasClick = async (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || !graphState.graphData) return;

    const { x: rawX, y: rawY } = getCanvasPoint(canvas, event.clientX, event.clientY);
    const x = (rawX - offset.x) / scale;
    const y = (rawY - offset.y) / scale;

    // Проверяем клик по иконке лестницы (приоритетнее всего в режимах view и edit)
    if ((mode === 'edit' || mode === 'view') && graphState.graphData) {
      const iconPositions = Array.from(ladderIconPositionsRef.current.entries());
      for (let i = 0; i < iconPositions.length; i++) {
        const [nodeId, iconPos] = iconPositions[i];
        const distance = Math.sqrt((iconPos.x - x) ** 2 + (iconPos.y - y) ** 2);
        if (distance < 12) { // Радиус иконки
          const ladderNode = graphState.graphData.nodes.find(n => n.id === nodeId);
          if (ladderNode) {
            setEditingLadderNode(ladderNode);
            setShowEditLadder(true);
            setSelectedNode(null);
            setSelectedTag(null);
            setSelectedPlace(null);
            setSelectedEdge(null);
            // Загружаем связанные узлы лестницы
            loadLadderConnections(ladderNode);
            event.preventDefault();
            return;
          }
        }
      }
    }

    switch (mode) {
      case 'addNode':
        handleAddNode(x, y);
        break;
      case 'addEdge':
        handleAddEdge(x, y);
        break;
      case 'addPlace':
        handleAddPlace(x, y);
        break;
      case 'addLadder':
        handleAddLadder(x, y);
        break;
      case 'edit':
        handleEditElement(x, y);
        break;
      case 'delete':
        handleDeleteElement(x, y);
        break;
      case 'view':
        handleSelectElement(x, y);
        break;
      case 'move':
        // В режиме перемещения не открываем попап, просто ничего не делаем
        break;
    }
  };

  const handleAddLadder = async (x: number, y: number) => {
    if (!graphState.selectedHorizon || !graphState.graphData) return;

    // Если еще не выбраны уровни - ничего не делаем (диалог уже открыт)
    if (ladderStep === 'selectLevels' || ladderStep === null) {
      return;
    }

    // Если выбраны уровни, но еще не выбран первый узел
    if (ladderStep === 'selectNode1' && ladderLevel1Id) {
      // Убеждаемся, что загружен правильный уровень
      if (graphState.selectedHorizon?.id !== ladderLevel1Id) {
        await graphState.loadGraphData(ladderLevel1Id);
        const level1 = graphState.horizons.find(h => h.id === ladderLevel1Id);
        if (level1) {
          graphState.setSelectedHorizon(level1);
        }
        // Перерисовываем после загрузки
        setTimeout(() => drawGraph(), 100);
        return;
      }

      // Находим ближайший узел к точке клика на первом уровне
      if (!graphState.graphData) {
        return;
      }
      
      const threshold = 20 / scale;
      let closestNode: GraphNode | null = null;
      let minDistance = threshold;

      for (const node of graphState.graphData.nodes) {
        if (node.horizon_id !== ladderLevel1Id) continue;
        
        const canvasCoords = settings.transformGPStoCanvas(node.y, node.x);
        const nodeX = canvasCoords.x;
        const nodeY = canvasCoords.y;
        
        const distance = Math.sqrt(Math.pow(nodeX - x, 2) + Math.pow(nodeY - y, 2));
        if (distance < minDistance) {
          closestNode = node;
          minDistance = distance;
        }
      }

      if (!closestNode) {
        alert('Не найдена вершина на первом уровне. Кликните ближе к существующей вершине.');
        return;
      }

      // TypeScript type guard - после проверки closestNode точно не null
      const selectedNode: GraphNode = closestNode;
      setLadderNode1Id(selectedNode.id);
      setLadderStep('selectNode2');
      
      // Переключаемся на второй уровень
      if (ladderLevel2Id) {
        await graphState.loadGraphData(ladderLevel2Id);
        const level2 = graphState.horizons.find(h => h.id === ladderLevel2Id);
        if (level2) {
          graphState.setSelectedHorizon(level2);
        }
        drawGraph();
        alert('Выберите узел на втором уровне');
      }
      return;
    }

    // Если выбран первый узел, выбираем второй узел на втором уровне
    if (ladderStep === 'selectNode2' && ladderLevel2Id) {
      // Убеждаемся, что загружен правильный уровень
      if (graphState.selectedHorizon?.id !== ladderLevel2Id) {
        await graphState.loadGraphData(ladderLevel2Id);
        const level2 = graphState.horizons.find(h => h.id === ladderLevel2Id);
        if (level2) {
          graphState.setSelectedHorizon(level2);
        }
        // Перерисовываем после загрузки
        setTimeout(() => drawGraph(), 100);
        return;
      }

      if (!graphState.graphData) {
        return;
      }
      
      const threshold = 20 / scale;
      let closestNode: GraphNode | null = null;
      let minDistance = threshold;

      for (const node of graphState.graphData.nodes) {
        if (node.horizon_id !== ladderLevel2Id) continue;
        
        const canvasCoords = settings.transformGPStoCanvas(node.y, node.x);
        const nodeX = canvasCoords.x;
        const nodeY = canvasCoords.y;
        
        const distance = Math.sqrt(Math.pow(nodeX - x, 2) + Math.pow(nodeY - y, 2));
        if (distance < minDistance) {
          closestNode = node;
          minDistance = distance;
        }
      }

      if (!closestNode) {
        alert('Не найдена вершина на втором уровне. Кликните ближе к существующей вершине.');
        return;
      }

      // TypeScript type guard - после проверки closestNode точно не null
      const selectedNode: GraphNode = closestNode;
      const node2Id = selectedNode.id;
      
      // Сохраняем ID первого узла в локальную переменную для надежности
      const node1Id = ladderNode1Id;
      
      if (!node1Id) {
        alert('Ошибка: не найден первый узел. Начните создание лестницы заново.');
        return;
      }
      
      setLadderNode2Id(node2Id);
      
      // Создаем лестницу сразу, передавая ID обоих узлов напрямую
      await handleCreateLadderBetweenNodes(node1Id, node2Id);
    }
  };

  const handleLadderConfirmTwoLevels = async (level1Id: number, level2Id: number) => {
    setLadderLevel1Id(level1Id);
    setLadderLevel2Id(level2Id);
    setLadderNode1Id(null);
    setLadderNode2Id(null);
    setShowLadderDialog(false);
    setLadderStep('selectNode1');
    
    // Переключаемся на первый уровень
    await graphState.loadGraphData(level1Id);
    const level1 = graphState.horizons.find(h => h.id === level1Id);
    if (level1) {
      graphState.setSelectedHorizon(level1);
    }
    drawGraph();
    alert('Выберите узел на первом уровне');
  };

  const handleCreateLadderBetweenNodes = async (node1Id?: number | null, node2Id?: number | null) => {
    // Используем переданные параметры или значения из состояния
    const fromNodeId = node1Id ?? ladderNode1Id;
    const toNodeId = node2Id ?? ladderNode2Id;
    
    if (!fromNodeId || !toNodeId) {
      alert('Не выбраны оба узла');
      return;
    }

    try {
      await connectLadderNodes(fromNodeId, toNodeId);
      
      // Сбрасываем состояние
      setLadderStep(null);
      setLadderLevel1Id(null);
      setLadderLevel2Id(null);
      setLadderNode1Id(null);
      setLadderNode2Id(null);
      setLadderSourceNode(null);
      
      // Перезагружаем граф для обновления
      await graphState.loadHorizons();
      if (graphState.selectedHorizon) {
        await graphState.loadGraphData(graphState.selectedHorizon.id);
      }
      
      alert('Лестница успешно создана!');
    } catch (error) {
      console.error('Error creating ladder:', error);
      alert('Ошибка при создании лестницы');
    }
  };

  const handleLadderConfirm = async (targetHorizonId: number) => {
    if (!ladderSourceNode || !graphState.selectedHorizon) return;

    try {
      // Преобразуем координаты узла обратно в Canvas координаты для API
      const canvasCoords = settings.transformGPStoCanvas(ladderSourceNode.y, ladderSourceNode.x);
      
      // Вызываем API для создания лестницы
      // Backend сам решит: связать с существующим узлом или создать новый
      await createLadder(graphState.selectedHorizon.id, { 
        x: canvasCoords.x, 
        y: canvasCoords.y,
        targetHorizonId // Передаём ID целевого горизонта
      });
      
      // Закрываем диалог
      setShowLadderDialog(false);
      setLadderSourceNode(null);
      
      // Перезагружаем граф для обновления
      await graphState.loadHorizons();
      await graphState.loadGraphData(graphState.selectedHorizon.id);
    } catch (error) {
      console.error('Error creating ladder:', error);
      alert('Ошибка при создании лестницы');
    }
  };

  const handleLadderCancel = () => {
    setShowLadderDialog(false);
    setLadderSourceNode(null);
    setLadderStep(null);
    setLadderLevel1Id(null);
    setLadderLevel2Id(null);
    setLadderNode1Id(null);
    setLadderNode2Id(null);
    drawGraph(); // Перерисовываем чтобы убрать визуальные индикаторы
  };

  // Функция загрузки связанных узлов лестницы
  const loadLadderConnections = async (node: GraphNode) => {
    if (!graphState.graphData) return;
    
    setLoadingLadderConnections(true);
    setLadderConnectedNodes([]);
    
    try {
      // Находим все вертикальные ребра, связанные с этим узлом
      const ladderEdges = graphState.graphData.edges.filter(edge => 
        (edge.from_node_id === node.id || edge.to_node_id === node.id) && 
        edge.edge_type === 'vertical'
      );
      
      const connectedNodes: Array<{node: GraphNode, edge: GraphEdge, horizon: Horizon}> = [];
      
      // Для каждого ребра находим связанный узел
      for (const edge of ladderEdges) {
        const connectedNodeId = edge.from_node_id === node.id ? edge.to_node_id : edge.from_node_id;
        
        // Сначала проверяем в текущем graphData
        let connectedNode: GraphNode | undefined = graphState.graphData.nodes.find(n => n.id === connectedNodeId);
        let connectedHorizon: Horizon | undefined;
        
        if (connectedNode) {
          connectedHorizon = graphState.horizons.find(h => h.id === connectedNode!.horizon_id);
        } else {
          // Если узла нет в текущем graphData, загружаем его через API
          try {
            // Пробуем найти узел через API - перебираем все уровни
            for (const horizon of graphState.horizons) {
              if (horizon.id === node.horizon_id) continue; // Пропускаем текущий уровень
              try {
                const graphData = await getHorizonGraph(horizon.id);
                const foundNode = graphData.nodes.find(n => n.id === connectedNodeId);
                if (foundNode) {
                  connectedNode = foundNode;
                  connectedHorizon = horizon;
                  break;
                }
              } catch (e) {
                // Продолжаем поиск
                continue;
              }
            }
          } catch (error) {
            console.error('Error loading connected node:', error);
          }
        }
        
        if (connectedNode && connectedHorizon) {
          connectedNodes.push({ node: connectedNode, edge, horizon: connectedHorizon });
        }
      }
      setLadderConnectedNodes(connectedNodes);
    } catch (error) {
      console.error('Error loading ladder connections:', error);
    } finally {
      setLoadingLadderConnections(false);
    }
  };

  const handleAddNode = async (x: number, y: number) => {
    if (!graphState.selectedHorizon) return;

    try {
      // ✅ Преобразуем canvas координаты обратно в GPS координаты
      const gpsCoords = settings.transformCanvasToGPS(x, y);
      
      const nodeData = {
        x: gpsCoords.lon,  // x = longitude
        y: gpsCoords.lat,  // y = latitude
        z: graphState.selectedHorizon.height,
        node_type: 'road'
      };
      
      await createNode(graphState.selectedHorizon.id, nodeData);
      graphState.loadGraphData(graphState.selectedHorizon.id);
    } catch (error) {
      console.error('Error creating node:', error);
    }
  };

  const handleAddEdge = async (x: number, y: number) => {
    if (!graphState.selectedHorizon || !graphState.graphData) return;

    // Поиск ближайшего узла
    const clickedNode = graphState.graphData.nodes.find(node => {
      // ✅ Преобразуем GPS координаты в canvas координаты
      const nodeCanvasPos = settings.transformGPStoCanvas(node.y, node.x);
      const distance = Math.sqrt((nodeCanvasPos.x - x) ** 2 + (nodeCanvasPos.y - y) ** 2);
      return distance < 15;
    });

    if (!clickedNode) return;

    if (selectedNode === null) {
      setSelectedNode(clickedNode.id);
    } else if (selectedNode !== clickedNode.id) {
      try {
        const edgeData = {
          from_node_id: selectedNode,
          to_node_id: clickedNode.id
        };
        
        await createEdge(graphState.selectedHorizon.id, edgeData);
        graphState.loadGraphData(graphState.selectedHorizon.id);
        setSelectedNode(null);
      } catch (error) {
        console.error('Error creating edge:', error);
      }
    }
  };

  const handleAddPlace = async (x: number, y: number) => {
    if (!graphState.selectedHorizon) return;

    try {
      // ✅ Преобразуем canvas координаты обратно в GPS координаты
      const gpsCoords = settings.transformCanvasToGPS(x, y);

      // Генерируем уникальное имя для места
      const generatePlaceName = () => `Место ${Date.now()}`;
      const generateTagId = () => `tag_${Date.now()}`;
      const generateTagMac = () => {
        const hex = () => Math.floor(Math.random() * 256).toString(16).padStart(2, '0').toUpperCase();
        return `${hex()}:${hex()}:${hex()}:${hex()}:${hex()}:${hex()}`;
      };
      const generateTagName = () => {
        const adjectives = ['Быстрый', 'Надежный', 'Умный', 'Сильный', 'Гибкий', 'Точный', 'Мощный', 'Легкий'];
        const nouns = ['Датчик', 'Маркер', 'Тег', 'Сенсор', 'Метка', 'Индикатор', 'Контроллер', 'Модуль'];
        const randomAdjective = adjectives[Math.floor(Math.random() * adjectives.length)];
        const randomNoun = nouns[Math.floor(Math.random() * nouns.length)];
        const randomNumber = Math.floor(Math.random() * 10000);
        return `${randomAdjective} ${randomNoun} ${randomNumber}`;
      };

      // Сначала создаем место
      const placeData = {
        name: generatePlaceName(),
        type: 'transit',  // Тип места по умолчанию
        location: {
          x: x,  // Canvas координаты X
          y: y,  // Canvas координаты Y
          lat: gpsCoords.lat,  // GPS широта
          lon: gpsCoords.lon   // GPS долгота
        },
        horizon_id: graphState.selectedHorizon.id
      };

      const createdPlace = await createPlace(placeData);

      // Затем создаем метку, привязанную к этому месту
      const tagData = {
        tag_id: generateTagId(),
        tag_mac: generateTagMac(),
        tag_name: generateTagName(),
        place_id: createdPlace.id,
        radius: 25.0
      };

      await createTag(tagData);
      graphState.loadGraphData(graphState.selectedHorizon.id);
    } catch (error) {
      console.error('Error creating place:', error);
    }
  };

  const handleSelectElement = (x: number, y: number) => {
    if (!graphState.graphData) return;
    
    // В режиме перемещения не открываем попап
    if (mode === 'move') {
      return;
    }
    
    // Локальная ссылка для TypeScript (non-null после проверки)
    const graphData = graphState.graphData!;

    // Проверяем клик по иконке лестницы (приоритетнее всего в режиме редактирования)
    if (mode === 'edit' || mode === 'view') {
      const iconPositions = Array.from(ladderIconPositionsRef.current.entries());
      for (let i = 0; i < iconPositions.length; i++) {
        const [nodeId, iconPos] = iconPositions[i];
        const distance = Math.sqrt((iconPos.x - x) ** 2 + (iconPos.y - y) ** 2);
        if (distance < 12) { // Радиус иконки
          const ladderNode = graphData.nodes.find(n => n.id === nodeId);
          if (ladderNode) {
            setEditingLadderNode(ladderNode);
            setShowEditLadder(true);
            setSelectedNode(null);
            setSelectedTag(null);
            setSelectedEdge(null);
            // Загружаем связанные узлы лестницы
            loadLadderConnections(ladderNode);
            return;
          }
        }
      }
    }

    // Проверяем клик по местам (places) — предпочитаем их, если они есть в ответе
    if (Array.isArray(graphData.places) && graphData.places.length > 0) {
      // Радиус клика в мировых координатах так, чтобы на экране оставалось ~12px
      const clickRadius = Math.max(8, Math.min(120, 12 / Math.max(0.1, scale)));

      const clickedPlace = graphData.places.find((place) => {
        const pos = getPlaceCanvasXY(place, settings.transformGPStoCanvas);
        if (!pos) return false;
        const distance = Math.sqrt((pos.x - x) ** 2 + (pos.y - y) ** 2);
        return distance < clickRadius;
      });

      if (clickedPlace) {
        setSelectedPlace(clickedPlace.id);
        setSelectedNode(null);
        setSelectedEdge(null);
        setSelectedTag(null);
        return;
      }
    }

    // Проверяем клик по legacy-меткам (только если places пустой)
    const activeTags = (Array.isArray(graphData.places) && graphData.places.length > 0) ? [] : graphData.tags;
    const clickedTag = activeTags.find(tag => {
      const lonLatFromPlace = tag.place ? getPlaceLonLat(tag.place) : null;
      const gpsLat: number = lonLatFromPlace?.lat ?? (tag.y ?? 0);
      const gpsLon: number = lonLatFromPlace?.lon ?? (tag.x ?? 0);
      const tagCanvasPos = settings.transformGPStoCanvas(gpsLat, gpsLon);
      const distance = Math.sqrt((tagCanvasPos.x - x) ** 2 + (tagCanvasPos.y - y) ** 2);
      return distance < (tag.radius || 25);
    });

    if (clickedTag) {
      setSelectedTag(clickedTag.id);
      setSelectedNode(null);
      setSelectedEdge(null);
      setSelectedPlace(null);
      // Явно закрываем окно редактирования - оно должно открываться только с инструментом "правка"
      setShowEditTag(false);
      setEditingTag(null);
      return;
    }

    // Проверяем клик по узлам
    const clickedNode = graphData.nodes.find(node => {
      // ✅ Преобразуем GPS координаты в canvas координаты
      const nodeCanvasPos = settings.transformGPStoCanvas(node.y, node.x);
      const distance = Math.sqrt((nodeCanvasPos.x - x) ** 2 + (nodeCanvasPos.y - y) ** 2);
      return distance < 15;
    });

    if (clickedNode) {
      setSelectedNode(clickedNode.id);
      setSelectedTag(null);
      setSelectedEdge(null);
      setSelectedPlace(null);
      // Явно закрываем окно редактирования - оно должно открываться только с инструментом "правка"
      setShowEditNode(false);
      setEditingNode(null);
      return;
    }

    // Проверяем клик по ребрам
    const clickedEdge = graphData.edges.find(edge => {
      const fromNode = graphData.nodes.find(n => n.id === edge.from_node_id);
      const toNode = graphData.nodes.find(n => n.id === edge.to_node_id);
      if (!fromNode || !toNode) return false;
      
      // Простая проверка расстояния до линии
      const distance = distanceToLine(x, y, fromNode.x, fromNode.y, toNode.x, toNode.y);
      return distance < 5;
    });

    if (clickedEdge) {
      setSelectedEdge(clickedEdge.id);
      setSelectedNode(null);
      setSelectedTag(null);
      setSelectedPlace(null);
      return;
    }

    // Ничего не выбрано
    setSelectedNode(null);
    setSelectedEdge(null);
    setSelectedTag(null);
    setSelectedPlace(null);
  };

  const handleEditElement = (x: number, y: number) => {
    if (!graphState.graphData) return;
    
    // Локальная ссылка для TypeScript
    const graphData = graphState.graphData!;

    // В режиме edit приоритетно даём выбрать place, если он есть (чтобы места "нажимались")
    if (Array.isArray(graphData.places) && graphData.places.length > 0) {
      const clickRadius = Math.max(8, Math.min(120, 12 / Math.max(0.1, scale)));
      const clickedPlace = graphData.places.find((place) => {
        const pos = getPlaceCanvasXY(place, settings.transformGPStoCanvas);
        if (!pos) return false;
        const distance = Math.sqrt((pos.x - x) ** 2 + (pos.y - y) ** 2);
        return distance < clickRadius;
      });

      if (clickedPlace) {
        setSelectedPlace(clickedPlace.id);
        setSelectedNode(null);
        setSelectedEdge(null);
        setSelectedTag(null);
        setShowEditTag(false);
        setShowEditNode(false);
        setShowEditEdge(false);
        return;
      }
    }

    // 1. Сначала ищем метку для редактирования
    const activeTags = (Array.isArray(graphData.places) && graphData.places.length > 0) ? [] : graphData.tags;
    const clickedTag = activeTags.find(tag => {
      const lonLatFromPlace = tag.place ? getPlaceLonLat(tag.place) : null;
      const gpsLat: number = lonLatFromPlace?.lat ?? (tag.y ?? 0);
      const gpsLon: number = lonLatFromPlace?.lon ?? (tag.x ?? 0);
      const tagCanvasPos = settings.transformGPStoCanvas(gpsLat, gpsLon);
      const distance = Math.sqrt((tagCanvasPos.x - x) ** 2 + (tagCanvasPos.y - y) ** 2);
      return distance < (tag.radius || 25);
    });

    if (clickedTag) {
      // Создаем новый объект, чтобы избежать проблем с readonly свойствами
      setEditingTag({...clickedTag});
      setTagError(null);
      setShowEditTag(true);
      return;
    }

    // 2. Если метки нет - ищем узел для редактирования
    const clickedNode = graphData.nodes.find(node => {
      // ✅ Преобразуем GPS координаты в canvas координаты
      const nodeCanvasPos = settings.transformGPStoCanvas(node.y, node.x);
      const distance = Math.sqrt((nodeCanvasPos.x - x) ** 2 + (nodeCanvasPos.y - y) ** 2);
      return distance < 15;  // Радиус клика для узла
    });

    if (clickedNode) {
      setEditingNode(clickedNode);
      setNodeError(null);
      setShowEditNode(true);
      return;
    }

    // 3. Если узла нет - ищем ребро для редактирования
    const clickedEdge = graphData.edges.find(edge => {
      const fromNode = graphData.nodes.find(n => n.id === edge.from_node_id);
      const toNode = graphData.nodes.find(n => n.id === edge.to_node_id);
      if (!fromNode || !toNode) return false;
      
      // Преобразуем координаты узлов
      const fromCanvasPos = settings.transformGPStoCanvas(fromNode.y, fromNode.x);
      const toCanvasPos = settings.transformGPStoCanvas(toNode.y, toNode.x);
      
      const distance = distanceToLine(x, y, fromCanvasPos.x, fromCanvasPos.y, toCanvasPos.x, toCanvasPos.y);
      return distance < 10;  // Радиус клика для ребра
    });

    if (clickedEdge) {
      setEditingEdge(clickedEdge);
      setEdgeError(null);
      setShowEditEdge(true);
      return;
    }
  };

  const handleDeleteElement = async (x: number, y: number) => {
    if (!graphState.graphData || !graphState.selectedHorizon) return;
    
    // Локальные ссылки для TypeScript
    const graphData = graphState.graphData!;
    const selectedHorizon = graphState.selectedHorizon!;

    // Удаление place (если places есть — это основной объект на карте)
    if (Array.isArray(graphData.places) && graphData.places.length > 0) {
      const clickRadius = Math.max(8, Math.min(120, 12 / Math.max(0.1, scale)));
      const clickedPlace = graphData.places.find((place) => {
        const pos = getPlaceCanvasXY(place, settings.transformGPStoCanvas);
        if (!pos) return false;
        const distance = Math.sqrt((pos.x - x) ** 2 + (pos.y - y) ** 2);
        return distance < clickRadius;
      });

      if (clickedPlace) {
        try {
          // Сначала удаляем связанные теги (бэкенд не даёт удалить место с тегами)
          const tagsToDelete = (graphData.tags || []).filter((t) => t.place_id === clickedPlace.id);
          for (const tag of tagsToDelete) {
            const res = await fetch(`/api/tags/${tag.id}`, { method: 'DELETE' });
            if (!res.ok) {
              const err = await res.json().catch(() => ({}));
              throw new Error(err.detail || err.message || `Не удалось удалить метку ${tag.id}`);
            }
          }
          const res = await fetch(`/api/places/${clickedPlace.id}`, { method: 'DELETE' });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || err.message || 'Не удалось удалить место');
          }
          graphState.loadGraphData(selectedHorizon.id);
          setSelectedPlace(null);
        } catch (error) {
          console.error('Error deleting place:', error);
        }
        return;
      }
    }

    // Проверяем клик по иконке лестницы (приоритетнее всего в режиме удаления)
    const iconPositions = Array.from(ladderIconPositionsRef.current.entries());
    for (let i = 0; i < iconPositions.length; i++) {
      const [nodeId, iconPos] = iconPositions[i];
      const distance = Math.sqrt((iconPos.x - x) ** 2 + (iconPos.y - y) ** 2);
      if (distance < 12) { // Радиус иконки
        const ladderNode = graphData.nodes.find(n => n.id === nodeId);
        if (ladderNode) {
          // Находим вертикальное ребро (лестницу), связанное с этим узлом
          const ladderEdge = graphData.edges.find(edge => 
            (edge.from_node_id === nodeId || edge.to_node_id === nodeId) && 
            edge.edge_type === 'vertical'
          );
          
          if (ladderEdge) {
            try {
              // Получаем информацию о обоих узлах перед удалением
              const fromNodeId = ladderEdge.from_node_id;
              const toNodeId = ladderEdge.to_node_id;
              
              // Получаем информацию о узлах из текущего graphData или через API
              const fromNode = graphData.nodes.find(n => n.id === fromNodeId);
              const toNode = graphData.nodes.find(n => n.id === toNodeId);
              
              // Собираем ID горизонтов для перезагрузки
              const horizonIdsToReload = new Set<number>();
              horizonIdsToReload.add(selectedHorizon.id);
              
              if (fromNode) {
                horizonIdsToReload.add(fromNode.horizon_id);
              }
              if (toNode) {
                horizonIdsToReload.add(toNode.horizon_id);
              }
              
              // Если один из узлов не найден в текущем graphData, ищем его в других горизонтах
              if (!fromNode || !toNode) {
                // Ищем узлы во всех доступных горизонтах
                for (const horizon of graphState.horizons) {
                  if (horizonIdsToReload.has(horizon.id)) continue; // Уже добавили
                  
                  try {
                    const graphResponse = await fetch(`/api/horizons/${horizon.id}/graph`);
                    if (graphResponse.ok) {
                      const horizonGraphData = await graphResponse.json();
                      const horizonNodes = horizonGraphData.nodes || [];
                      
                      const foundFromNode = horizonNodes.find((n: any) => n.id === fromNodeId);
                      const foundToNode = horizonNodes.find((n: any) => n.id === toNodeId);
                      
                      if (foundFromNode) {
                        horizonIdsToReload.add(foundFromNode.horizon_id);
                      }
                      if (foundToNode) {
                        horizonIdsToReload.add(foundToNode.horizon_id);
                      }
                      
                      // Если нашли оба узла, можно прекратить поиск
                      if ((fromNode || foundFromNode) && (toNode || foundToNode)) {
                        break;
                      }
                    }
                  } catch (apiError) {
                    // Продолжаем поиск в других горизонтах
                    continue;
                  }
                }
              }
              
              // Удаляем ребро
              await fetch(`/api/edges/${ladderEdge.id}`, { method: 'DELETE' });
              
              // Перезагружаем данные на всех затронутых горизонтах
              for (const horizonId of Array.from(horizonIdsToReload)) {
                await graphState.loadGraphData(horizonId);
              }
            } catch (error) {
              console.error('Error deleting ladder edge:', error);
            }
            return;
          }
        }
      }
    }

    // Удаление legacy-метки (только если places пустой)
    const activeTags = (Array.isArray(graphData.places) && graphData.places.length > 0) ? [] : graphData.tags;
    const clickedTag = activeTags.find(tag => {
      const lonLatFromPlace = tag.place ? getPlaceLonLat(tag.place) : null;
      const gpsLat: number = lonLatFromPlace?.lat ?? (tag.y ?? 0);
      const gpsLon: number = lonLatFromPlace?.lon ?? (tag.x ?? 0);
      const tagCanvasPos = settings.transformGPStoCanvas(gpsLat, gpsLon);
      const distance = Math.sqrt((tagCanvasPos.x - x) ** 2 + (tagCanvasPos.y - y) ** 2);
      return distance < (tag.radius || 25);
    });

    if (clickedTag) {
      try {
        await fetch(`/api/tags/${clickedTag.id}`, { method: 'DELETE' });
        graphState.loadGraphData(selectedHorizon.id);
      } catch (error) {
        console.error('Error deleting tag:', error);
      }
      return;
    }

    // Удаление узла
    const clickedNode = graphData.nodes.find(node => {
      // ✅ Преобразуем GPS координаты в canvas координаты
      const nodeCanvasPos = settings.transformGPStoCanvas(node.y, node.x);
      const distance = Math.sqrt((nodeCanvasPos.x - x) ** 2 + (nodeCanvasPos.y - y) ** 2);
      return distance < 15;
    });

    if (clickedNode) {
      try {
        await fetch(`/api/nodes/${clickedNode.id}`, { method: 'DELETE' });
        graphState.loadGraphData(selectedHorizon.id);
      } catch (error) {
        console.error('Error deleting node:', error);
      }
      return;
    }

    // Удаление ребра (дороги)
    const clickedEdge = graphData.edges.find(edge => {
      const fromNode = graphData.nodes.find(n => n.id === edge.from_node_id);
      const toNode = graphData.nodes.find(n => n.id === edge.to_node_id);
      if (!fromNode || !toNode) return false;
      
      // ✅ Преобразуем GPS координаты узлов в canvas координаты
      const fromCanvasPos = settings.transformGPStoCanvas(fromNode.y, fromNode.x);
      const toCanvasPos = settings.transformGPStoCanvas(toNode.y, toNode.x);
      
      const distance = distanceToLine(x, y, fromCanvasPos.x, fromCanvasPos.y, toCanvasPos.x, toCanvasPos.y);
      return distance < 10; // Увеличиваем радиус для лучшего попадания
    });

    if (clickedEdge) {
      try {
        await fetch(`/api/edges/${clickedEdge.id}`, { method: 'DELETE' });
        graphState.loadGraphData(selectedHorizon.id);
      } catch (error) {
        console.error('Error deleting edge:', error);
      }
      return;
    }
  };

  const distanceToLine = (px: number, py: number, x1: number, y1: number, x2: number, y2: number): number => {
    const A = px - x1;
    const B = py - y1;
    const C = x2 - x1;
    const D = y2 - y1;

    const dot = A * C + B * D;
    const lenSq = C * C + D * D;
    let param = -1;

    if (lenSq !== 0) {
      param = dot / lenSq;
    }

    let xx, yy;

    if (param < 0) {
      xx = x1;
      yy = y1;
    } else if (param > 1) {
      xx = x2;
      yy = y2;
    } else {
      xx = x1 + param * C;
      yy = y1 + param * D;
    }

    const dx = px - xx;
    const dy = py - yy;

    return Math.sqrt(dx * dx + dy * dy);
  };

  const handleUpdateTag = async () => {
    if (!editingTag) return;
    
    // Очистить предыдущие ошибки
    setTagError(null);

    try {
      // Обновляем только поля метки (Tag) - БЕЗ координат (они теперь в Place)
      const updateData = {
        tag_id: editingTag.tag_id || editingTag.beacon_id || editingTag.point_id || '',
        tag_mac: editingTag.tag_mac || editingTag.beacon_mac || '',
        radius: editingTag.radius || 25
        // Координаты (x, y, name, type) теперь хранятся в Place, не в Tag
      };
      
      const response = await fetch(`/api/tags/${editingTag.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData)
      });

      if (response.ok) {
        graphState.loadGraphData(graphState.selectedHorizon!.id);
        setShowEditTag(false);
        setEditingTag(null);
        setTagError(null);
      } else {
        // Парсим ошибку от backend
        const errorData = await response.json();
        const errorMessage = errorData.error || errorData.detail || 'Ошибка при обновлении метки';
        setTagError(errorMessage);
        console.error('Error updating tag:', errorData);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Неизвестная ошибка';
      setTagError(`Ошибка сети: ${message}`);
      console.error('Error updating tag:', error);
    }
  };

  const handleUpdatePlace = async () => {
    if (!editingPlace) return;

    setPlaceError(null);

    try {
      const updateData: any = {
        name: editingPlace.name,
        type: editingPlace.type,
        cargo_type: editingPlace.cargo_type ?? null,
      };

      const response = await fetch(`/api/places/${editingPlace.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData),
      });

      if (response.ok) {
        if (graphState.selectedHorizon) {
          await graphState.loadGraphData(graphState.selectedHorizon.id);
        }
        setShowEditPlace(false);
        setEditingPlace(null);
        setPlaceError(null);
      } else {
        let message = 'Ошибка при обновлении места';
        try {
          const errorData = await response.json();
          message = errorData.detail || errorData.error || message;
        } catch {
          /* ignore parse error */
        }
        setPlaceError(message);
        console.error('Error updating place:', message);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Неизвестная ошибка';
      setPlaceError(`Ошибка сети: ${message}`);
      console.error('Error updating place:', error);
    }
  };

  const handleZoom = (delta: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;
    
    // Центр холста в координатах canvas
    const centerX = canvasWidth / 2;
    const centerY = canvasHeight / 2;
    
    // Используем функциональное обновление для получения актуальных значений
    setScale(prevScale => {
      setOffset(prevOffset => {
        // Преобразуем центр холста в мировые координаты (до зума)
        const worldCenterX = (centerX - prevOffset.x) / prevScale;
        const worldCenterY = (centerY - prevOffset.y) / prevScale;
        
        // Новый scale (увеличиваем макс. до 10 вместо 5)
        const newScale = Math.max(0.1, Math.min(10, prevScale + delta));
        
        // Вычисляем новый offset, чтобы центр остался в том же месте
        const newOffsetX = centerX - worldCenterX * newScale;
        const newOffsetY = centerY - worldCenterY * newScale;
        
        return { x: newOffsetX, y: newOffsetY };
      });
      
      return Math.max(0.1, Math.min(10, prevScale + delta));
    });
  };

  const handlePan = (dx: number, dy: number) => {
    setOffset(prevOffset => ({ x: prevOffset.x + dx, y: prevOffset.y + dy }));
  };
  
  // Функция автоматического масштабирования графа под размер холста
  const fitGraphToCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !graphState.graphData) return;
    
    const { nodes, tags, places } = graphState.graphData;
    const mapPlaces = Array.isArray(places) && places.length > 0 ? places : null;
    
    // Если нет узлов и меток, не масштабируем
    if (nodes.length === 0 && (mapPlaces ? mapPlaces.length === 0 : tags.length === 0)) return;
    
    // Находим границы всех объектов графа
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    
    // Учитываем узлы
    nodes.forEach(node => {
      // ✅ Преобразуем GPS координаты в canvas координаты
      const canvasPos = settings.transformGPStoCanvas(node.y, node.x);
      
      // 🔍 ЗАЩИТА: Проверяем что координаты адекватные (не миллионы)
      if (Math.abs(canvasPos.x) > 100000 || Math.abs(canvasPos.y) > 100000) {
        return; // Пропускаем этот узел
      }
      
      minX = Math.min(minX, canvasPos.x);
      maxX = Math.max(maxX, canvasPos.x);
      minY = Math.min(minY, canvasPos.y);
      maxY = Math.max(maxY, canvasPos.y);
    });
    
    // Учитываем точки places (предпочтительно) или fallback на tags
    if (mapPlaces) {
      mapPlaces.forEach((place: Place) => {
        const canvasPos = getPlaceCanvasXY(place, settings.transformGPStoCanvas);
        if (!canvasPos) return;

        // 🔍 ЗАЩИТА: Проверяем что координаты адекватные
        if (Math.abs(canvasPos.x) > 100000 || Math.abs(canvasPos.y) > 100000) {
          return;
        }

        const pointPadding = 15;
        minX = Math.min(minX, canvasPos.x - pointPadding);
        maxX = Math.max(maxX, canvasPos.x + pointPadding);
        minY = Math.min(minY, canvasPos.y - pointPadding);
        maxY = Math.max(maxY, canvasPos.y + pointPadding);
      });
    } else {
      // Учитываем метки с их радиусами (legacy)
      tags.forEach(tag => {
        const lonLatFromPlace = tag.place ? getPlaceLonLat(tag.place) : null;
        const gpsLat: number = lonLatFromPlace?.lat ?? (tag.y ?? 0);
        const gpsLon: number = lonLatFromPlace?.lon ?? (tag.x ?? 0);
        const canvasPos = settings.transformGPStoCanvas(gpsLat, gpsLon);
        
        // 🔍 ЗАЩИТА: Проверяем что координаты адекватные
        if (Math.abs(canvasPos.x) > 100000 || Math.abs(canvasPos.y) > 100000) {
          return; // Пропускаем эту метку
        }
        
        const tagRadius = tag.radius || 25;
        minX = Math.min(minX, canvasPos.x - tagRadius);
        maxX = Math.max(maxX, canvasPos.x + tagRadius);
        minY = Math.min(minY, canvasPos.y - tagRadius);
        maxY = Math.max(maxY, canvasPos.y + tagRadius);
      });
    }
    
    // Если границы невалидные, используем дефолтные значения
    if (!isFinite(minX) || !isFinite(maxX) || !isFinite(minY) || !isFinite(maxY)) {
      setScale(1);
      setOffset({ x: 0, y: 0 });
      return;
    }
    
    // Размеры графа
    const graphWidth = maxX - minX;
    const graphHeight = maxY - minY;
    
    // ВАЖНО: Если граф слишком маленький (< 50м), устанавливаем минимальный размер
    // Это предотвращает слишком большой zoom для маленьких графов
    const minGraphSize = 50; // Минимальный размер графа в метрах
    const effectiveGraphWidth = Math.max(graphWidth, minGraphSize);
    const effectiveGraphHeight = Math.max(graphHeight, minGraphSize);
    
    // Размеры холста
    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;
    
    // Padding (20% от размера холста для более комфортного обзора)
    const paddingX = canvasWidth * 0.2;
    const paddingY = canvasHeight * 0.2;
    
    // Вычисляем scale, чтобы граф уместился с учетом padding
    const scaleX = (canvasWidth - 2 * paddingX) / effectiveGraphWidth;
    const scaleY = (canvasHeight - 2 * paddingY) / effectiveGraphHeight;
    const newScale = Math.max(0.5, Math.min(scaleX, scaleY, 10)); // Ограничиваем scale: 0.5x - 10x
    
    // Центр графа в мировых координатах
    const graphCenterX = (minX + maxX) / 2;
    const graphCenterY = (minY + maxY) / 2;
    
    // Центр холста
    const canvasCenterX = canvasWidth / 2;
    const canvasCenterY = canvasHeight / 2;
    
    // Вычисляем offset для центрирования графа
    const newOffsetX = canvasCenterX - graphCenterX * newScale;
    const newOffsetY = canvasCenterY - graphCenterY * newScale;
    
    setScale(newScale);
    setOffset({ x: newOffsetX, y: newOffsetY });
  }, [graphState.graphData]);

  const handleCreateHorizon = async (name: string, height: number, color?: string) => {
    const levelData = {
      name,
      height,
      color: color || COLOR_ACCENT,
      description: `Горизонт на высоте ${height}м`
    };
    
    const newHorizon = await createHorizon(levelData);
    await graphState.loadHorizons();
    graphState.setSelectedHorizon(newHorizon);
  };
  
  const handleDeleteHorizon = async (levelId: number) => {
    try {
      // Получаем информацию об объектах на горизонте
      const objectsInfo = await getHorizonObjectsCount(levelId);
      
      // Формируем предупреждение
      const objectsList = [];
      if (objectsInfo.objects.nodes > 0) objectsList.push(`Узлов: ${objectsInfo.objects.nodes}`);
      if (objectsInfo.objects.edges > 0) objectsList.push(`Дорог: ${objectsInfo.objects.edges}`);
      if (objectsInfo.objects.tags > 0) objectsList.push(`Меток: ${objectsInfo.objects.tags}`);
      if (objectsInfo.objects.ladders > 0) objectsList.push(`Лестниц: ${objectsInfo.objects.ladders}`);
      
      const confirmMessage = objectsInfo.total > 0
        ? `ВНИМАНИЕ! Будут безвозвратно удалены следующие объекты:\n\n${objectsList.join('\n')}\n\nВсего объектов: ${objectsInfo.total}\n\nПродолжить?`
        : `Удалить горизонт "${objectsInfo.level_name}"?`;
      
      if (!window.confirm(confirmMessage)) {
        return;
      }
      
      const removedSelected = graphState.selectedHorizon?.id === levelId;
      
      // Удаляем уровень
      await deleteHorizon(levelId);
      
      // Если удаляем текущий горизонт — временно сбрасываем выбор, чтобы не отображать устаревшие данные
      if (removedSelected) {
        graphState.setSelectedHorizon(null);
        graphState.setGraphData(null);
      }
      
      // Перезагружаем список горизонтов и получаем актуальные данные
      const updatedHorizons = await graphState.loadHorizons();
      
      // Выбираем первый доступный горизонт (если удаленный был выбран)
      if (removedSelected) {
        const nextHorizon = updatedHorizons.length > 0 ? updatedHorizons[0] : null;
        graphState.setSelectedHorizon(nextHorizon);
        if (nextHorizon) {
          await graphState.loadGraphData(nextHorizon.id);
        } else {
          graphState.setGraphData(null);
        }
      }
      
      alert('Горизонт успешно удален');
    } catch (error) {
      console.error('Error deleting level:', error);
      throw error;
    }
  };

  const handleViewChange = (view: 'settings' | 'graphs' | 'editor' | 'viewer') => {
    if (view === 'viewer') {
      navigate('/');
    } else {
      setCurrentView(view);
    }
  };

  const handleImportSuccess = async (importedHorizonIds: number[]) => {
    // Перезагружаем список горизонтов после успешного импорта
    await graphState.loadHorizons();
    
    // Выбираем первый импортированный горизонт
    if (importedHorizonIds.length > 0 && graphState.horizons.length > 0) {
      const importedHorizonId = importedHorizonIds[0];
      const importedHorizon = graphState.horizons.find(level => level.id === importedHorizonId);
      
      if (importedHorizon) {
        graphState.setSelectedHorizon(importedHorizon);
      } else {
        graphState.setSelectedHorizon(graphState.horizons[0]);
      }
    } else if (graphState.horizons.length > 0) {
      // Если horizon_ids не переданы, выбираем последний (самый новый) горизонт
      const lastHorizon = graphState.horizons[graphState.horizons.length - 1];
      graphState.setSelectedHorizon(lastHorizon);
    }
  };

  // Центрирование камеры на truck
  const centerOnVehicle = (vehicle: VehiclePosition) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;

    // Трансформируем GPS координаты в Canvas координаты
    const { x: canvasX, y: canvasY } = settings.transformGPStoCanvas(vehicle.lat, vehicle.lon);

    // Центрируем offset так, чтобы vehicle оказался в центре canvas
    const newOffsetX = canvasWidth / 2 - canvasX * scale;
    const newOffsetY = canvasHeight / 2 - canvasY * scale;

    setOffset({ x: newOffsetX, y: newOffsetY });
  };

  // Сохранение настроек
  const handleSaveSettings = () => {
    // Сохраняем только координаты
    settings.saveSettings({
      coordinateCalibration: settings.coordinateCalibration
    });
    setCurrentView('editor');
  };

  // Автоматическое масштабирование графа ТОЛЬКО при смене уровня (не при каждом обновлении данных)
  useEffect(() => {
    const currentHorizonId = graphState.selectedHorizon?.id || null;
    
    // Вызываем fitGraphToCanvas ТОЛЬКО если уровень реально изменился
    if (currentHorizonId !== previousHorizonId && graphState.graphData && canvasRef.current) {
      // Небольшая задержка, чтобы canvas успел отрендериться
      const timeoutId = setTimeout(() => {
        fitGraphToCanvas();
        setPreviousHorizonId(currentHorizonId); // Обновляем отслеживание
      }, 100);
      
      return () => clearTimeout(timeoutId);
    } else if (currentHorizonId !== previousHorizonId) {
      // Обновляем previousHorizonId даже если нет данных
      setPreviousHorizonId(currentHorizonId);
    }
  }, [graphState.selectedHorizon, graphState.graphData, previousHorizonId, fitGraphToCanvas]);

  useEffect(() => {
    const handleWindowMouseUp = () => {
      handleMouseUp();
    };

    window.addEventListener('mouseup', handleWindowMouseUp);
    return () => {
      window.removeEventListener('mouseup', handleWindowMouseUp);
    };
  }, [handleMouseUp]);

  const [isHorizonsModalOpen, setIsHorizonsModalOpen] = useState(false);
  const [horizonDetails, setHorizonDetails] = useState<Record<number, GraphData> | null>(null);
  const [isHorizonsModalLoading, setIsHorizonsModalLoading] = useState(false);
  const [horizonsModalError, setHorizonsModalError] = useState<string | null>(null);
  const [expandedHorizons, setExpandedHorizons] = useState<number[]>([]);

  const loadHorizonsDetails = useCallback(async () => {
    if (!Array.isArray(graphState.horizons) || graphState.horizons.length === 0) {
      setHorizonDetails({});
      return;
    }

    setIsHorizonsModalLoading(true);
    setHorizonsModalError(null);
    try {
      const entries = await Promise.all(
        graphState.horizons.map(async (horizon) => {
          const data = await getHorizonGraph(horizon.id);
          return [horizon.id, data] as [number, GraphData];
        })
      );

      setHorizonDetails(Object.fromEntries(entries));
    } catch (error) {
      console.error('Failed to load horizons data', error);
      setHorizonsModalError('Не удалось загрузить данные горизонтов');
    } finally {
      setIsHorizonsModalLoading(false);
    }
  }, [graphState.horizons]);

  useEffect(() => {
    setHorizonDetails(null);
  }, [graphState.horizons]);

  const handleOpenHorizonsModal = () => {
    setIsHorizonsModalOpen(true);
    setExpandedHorizons([]);
    if (!horizonDetails || Object.keys(horizonDetails).length !== graphState.horizons.length) {
      loadHorizonsDetails();
    }
  };

  const handleCloseHorizonsModal = () => {
    setIsHorizonsModalOpen(false);
  };

  useEffect(() => {
    if (isHorizonsModalOpen && (!horizonDetails || Object.keys(horizonDetails).length !== graphState.horizons.length) && !isHorizonsModalLoading) {
      loadHorizonsDetails();
    }
  }, [isHorizonsModalOpen, horizonDetails, graphState.horizons, isHorizonsModalLoading, loadHorizonsDetails]);

  const toggleHorizonExpanded = (id: number) => {
    setExpandedHorizons(prev =>
      prev.includes(id) ? prev.filter(hId => hId !== id) : [...prev, id]
    );
  };

  // Функция для перевода типа метки в читаемый формат
  const getTagTypeLabel = (pointType: string): string => {
    const typeMap: Record<string, string> = {
      'transit': 'Транзитное место',
      'loading': 'Место погрузки',
      'transfer': 'Место перегрузки',
      'unloading': 'Место разгрузки',
        'transport': 'Место стоянки'
      };
      return typeMap[pointType] || pointType;
    };

    // Функция для показа места на карте (центрирование камеры на координатах места)
    const showPlaceOnMap = (place: Place) => {
      // Закрываем модальное окно
      setIsHorizonsModalOpen(false);

      // Переключаемся в режим редактирования (view, не edit!)
      handleViewChange('editor');

      // Находим горизонт места и выбираем его
      const placeHorizonId = place.horizon_id ?? place.horizon?.id;
      const placeHorizon = placeHorizonId ? graphState.horizons.find(h => h.id === placeHorizonId) : null;
      if (placeHorizon) {
        graphState.setSelectedHorizon(placeHorizon);
      }

      // Загружаем данные графа для выбранного горизонта, если они еще не загружены
      if (placeHorizon && (!graphState.graphData || graphState.graphData.horizon?.id !== placeHorizon.id)) {
        graphState.loadGraphData(placeHorizon.id);
      }

      // Центрируем камеру на месте (увеличиваем задержку для загрузки данных)
      setTimeout(() => {
        const canvas = canvasRef.current;
        if (!canvas) {
          setTimeout(() => showPlaceOnMap(place), 200);
          return;
        }

        const canvasPos = getPlaceCanvasXY(place, settings.transformGPStoCanvas);
        if (!canvasPos) return;

        const canvasWidth = canvas.width;
        const canvasHeight = canvas.height;

        const canvasX = canvasPos.x;
        const canvasY = canvasPos.y;

        // Центрируем offset так, чтобы место оказалось в центре canvas
        const newOffsetX = canvasWidth / 2 - canvasX * scale;
        const newOffsetY = canvasHeight / 2 - canvasY * scale;

        setOffset({ x: newOffsetX, y: newOffsetY });

        // Сбрасываем выделение legacy-тегов, чтобы не показывать устаревшую карточку
        setSelectedTag(null);
        setShowEditTag(false);
      }, 300);
    };

    // Legacy: Функция для показа метки на карте (используем только если places пустой)
    const showTagOnMap = (tag: Tag) => {
      // Закрываем модальное окно
      setIsHorizonsModalOpen(false);
      
      // Переключаемся в режим редактирования (view, не edit!)
      handleViewChange('editor');
      
      // Находим горизонт метки и выбираем его
      const tagHorizon = graphState.horizons.find(h => h.id === (tag.horizon_id ?? tag.place?.horizon_id));
      if (tagHorizon) {
        graphState.setSelectedHorizon(tagHorizon);
      }
      
      // Загружаем данные графа для выбранного горизонта, если они еще не загружены
      if (tagHorizon && (!graphState.graphData || graphState.graphData.horizon?.id !== tagHorizon.id)) {
        graphState.loadGraphData(tagHorizon.id);
      }
      
      // Центрируем камеру на метке (увеличиваем задержку для загрузки данных)
      setTimeout(() => {
        const canvas = canvasRef.current;
        if (!canvas) {
          setTimeout(() => showTagOnMap(tag), 200);
          return;
        }

      const canvasWidth = canvas.width;
      const canvasHeight = canvas.height;

      // Трансформируем координаты метки в Canvas координаты (fallback)
      const lonLatFromPlace = tag.place ? getPlaceLonLat(tag.place) : null;
      const gpsLat: number = lonLatFromPlace?.lat ?? (tag.y ?? 0);
      const gpsLon: number = lonLatFromPlace?.lon ?? (tag.x ?? 0);
      const { x: canvasX, y: canvasY } = settings.transformGPStoCanvas(gpsLat, gpsLon);

      // Центрируем offset так, чтобы метка оказалась в центре canvas
      const newOffsetX = canvasWidth / 2 - canvasX * scale;
      const newOffsetY = canvasHeight / 2 - canvasY * scale;

      setOffset({ x: newOffsetX, y: newOffsetY });
      
      // Выделяем метку (но НЕ открываем окно редактирования!)
      setSelectedTag(tag.id);
      setShowEditTag(false); // Явно закрываем окно редактирования
    }, 300); // Увеличена задержка для загрузки данных
  };

  const showNodeOnMap = (node: GraphNode) => {
    // Закрываем модальное окно
    setIsHorizonsModalOpen(false);
    
    // Переключаемся в режим редактирования (view, не edit!)
    handleViewChange('editor');
    
    // Находим горизонт узла и выбираем его
    const nodeHorizon = graphState.horizons.find(h => h.id === node.horizon_id || Math.abs(h.height - node.z) < 5);
    if (nodeHorizon) {
      graphState.setSelectedHorizon(nodeHorizon);
    }
    
    // Загружаем данные графа для выбранного горизонта, если они еще не загружены
    if (nodeHorizon && (!graphState.graphData || graphState.graphData.horizon?.id !== nodeHorizon.id)) {
      graphState.loadGraphData(nodeHorizon.id);
    }
    
    // Центрируем камеру на узле
    setTimeout(() => {
      const canvas = canvasRef.current;
      if (!canvas) {
        setTimeout(() => showNodeOnMap(node), 200);
        return;
      }

      const canvasWidth = canvas.width;
      const canvasHeight = canvas.height;

      // Трансформируем координаты узла в Canvas координаты
      const { x: canvasX, y: canvasY } = settings.transformGPStoCanvas(node.y, node.x);

      // Центрируем offset так, чтобы узел оказался в центре canvas
      const newOffsetX = canvasWidth / 2 - canvasX * scale;
      const newOffsetY = canvasHeight / 2 - canvasY * scale;

      setOffset({ x: newOffsetX, y: newOffsetY });
      
      // Выделяем узел (но НЕ открываем окно редактирования!)
      setSelectedNode(node.id);
      setShowEditNode(false); // Явно закрываем окно редактирования
    }, 300); // Увеличена задержка для загрузки данных
  };

  return (
    <div className="graph-editor">
      {/* Header с навигацией */}
      <AppHeader currentView={currentView} onViewChange={handleViewChange} onShowHorizonsModal={handleOpenHorizonsModal} />

      {/* Режим настроек */}
      {currentView === 'settings' && (
        <SettingsPage
          coordinateCalibration={settings.coordinateCalibration}
          onCoordinateCalibrationChange={settings.setCoordinateCalibration}
          onCancel={() => setCurrentView('editor')}
          onSave={handleSaveSettings}
        />
      )}

      {/* Режим редактирования */}
      {currentView === 'editor' && (
        <div className="editor-layout">
          <div className="left-dock">
            <div className="dock-buttons">
              <button
                type="button"
                className={`dock-button ${leftDockSelection === 'horizons' ? 'active' : ''}`}
                onClick={() => {
                  setLeftDockSelection('horizons');
                  setIsLeftPanelOpen(true);
                }}
                title="Горизонты"
                aria-pressed={leftDockSelection === 'horizons'}
              >
                <span aria-hidden="true">🧭</span>
                <span className="sr-only">Горизонты</span>
              </button>
              <button
                type="button"
                className={`dock-button ${leftDockSelection === 'tools' ? 'active' : ''}`}
                onClick={() => {
                  setLeftDockSelection('tools');
                  setIsLeftPanelOpen(true);
                }}
                title="Инструменты"
                aria-pressed={leftDockSelection === 'tools'}
              >
                <span aria-hidden="true">🛠</span>
                <span className="sr-only">Инструменты</span>
              </button>
            </div>
            {isLeftPanelOpen && leftDockSelection && (
              <aside
                className="side-panel left open"
                style={leftPanelStyle}
              >
                <div className="panel-shell">
                  <div className={`panel-body ${isLeftPanelOpen ? 'visible' : 'hidden'}`}>
                    <div className="panel-scroll">
                      <EditorToolbar
                        isOpen={isLeftPanelOpen}
                        activeTab={leftDockSelection!}
                        horizons={Array.isArray(graphState.horizons) ? graphState.horizons : []}
                        selectedHorizon={graphState.selectedHorizon}
                        onHorizonChange={graphState.setSelectedHorizon}
                        onCreateHorizon={handleCreateHorizon}
                        onDeleteHorizon={handleDeleteHorizon}
                        onImportGraph={() => setShowImportDialog(true)}
                        mode={mode}
                        onModeChange={(newMode) => {
                          // Сброс состояния лестницы при смене режима
                          if (mode === 'addLadder' && newMode !== 'addLadder') {
                            setLadderStep(null);
                            setLadderLevel1Id(null);
                            setLadderLevel2Id(null);
                            setLadderNode1Id(null);
                            setLadderNode2Id(null);
                            setLadderSourceNode(null);
                            setShowLadderDialog(false);
                            drawGraph();
                          }
                          // При выборе инструмента лестница сразу открываем диалог выбора уровней
                          if (newMode === 'addLadder') {
                            setLadderStep('selectLevels');
                            setLadderLevel1Id(null);
                            setLadderLevel2Id(null);
                            setLadderNode1Id(null);
                            setLadderNode2Id(null);
                            setLadderSourceNode(null);
                            setShowLadderDialog(true);
                          }
                          setMode(newMode);
                        }}
                        scale={scale}
                        offset={offset}
                        onZoom={handleZoom}
                        onResetView={fitGraphToCanvas}
                        cursorPos={cursorPos}
                        onClosePanel={() => setIsLeftPanelOpen(false)}
                      />
                    </div>
                  </div>
                </div>
              </aside>
            )}
          </div>

          <div className="canvas-column">
            <div className="canvas-wrapper">
              {/* Отображение имени горизонта в верхнем левом углу */}
              {graphState.selectedHorizon && (
                <div className="horizon-label">
                  {graphState.selectedHorizon.name}
                </div>
              )}
              <canvas
                ref={canvasRef}
                width={980}
                height={680}
                className={
                  isDraggingRadius ? ''
                    : isDraggingObject ? ''
                    : isPanning ? 'cursor-move panning'
                    : mode === 'move' ? 'cursor-move'
                    : mode === 'view' ? 'cursor-pointer'
                    : 'cursor-crosshair'
                }
                onClick={handleCanvasClick}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseLeave}
                style={{
                  width: '100%',
                  height: '100%',
                  cursor: isDraggingRadius ? 'ew-resize'
                    : isDraggingObject ? 'move'
                    : undefined,
                }}
              />
              {cursorPos && (
                <div className="canvas-coordinates">
                  X: {cursorPos.x.toFixed(1)} • Y: {cursorPos.y.toFixed(1)}
                </div>
              )}
              {mode === 'addLadder' && ladderStep !== null && (
                <div className="ladder-hint" style={{
                  position: 'absolute',
                  top: '10px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  backgroundColor: 'rgba(44, 44, 44, 0.95)',
                  color: '#FEFCF9',
                  padding: '12px 20px',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: 'bold',
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
                  zIndex: 1000,
                  border: '2px solid #D15C29',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px'
                }}>
                  <span>🪜</span>
                  <span>
                    {ladderStep === 'selectLevels' && 'Выберите два уровня в диалоге'}
                    {ladderStep === 'selectNode1' && `Выберите узел на уровне "${graphState.horizons.find(h => h.id === ladderLevel1Id)?.name || 'Уровень 1'}"`}
                    {ladderStep === 'selectNode2' && `Выберите узел на уровне "${graphState.horizons.find(h => h.id === ladderLevel2Id)?.name || 'Уровень 2'}"`}
                  </span>
                  {ladderNode1Id && (
                    <span style={{ color: '#2ecc71', marginLeft: '10px' }}>✓ Узел 1 выбран</span>
                  )}
                  {ladderNode2Id && (
                    <span style={{ color: '#3498db', marginLeft: '10px' }}>✓ Узел 2 выбран</span>
                  )}
                </div>
              )}
            </div>

            {/* Попап выбора элемента в правом верхнем углу */}
            {hasSelection && !showEditNode && !showEditTag && !showEditEdge && !showEditLadder && (
              <div className="selection-popup" role="dialog">
                <button
                  type="button"
                  className="selection-popup-close"
                  onClick={() => {
                    setSelectedNode(null);
                    setSelectedEdge(null);
                    setSelectedTag(null);
                    setSelectedPlace(null);
                  }}
                  aria-label="Закрыть"
                >
                  ✕
                </button>
                <div className="selection-popup-content">
                  {selectedPlace && graphState.graphData && Array.isArray(graphState.graphData.places) && (
                    <div className="selection-info">
                      {(() => {
                        const place = graphState.graphData.places!.find((p) => p.id === selectedPlace);
                        const r = place ? placeRadiusMap.get(place.id) : undefined;
                        if (!place) return null;
                        return (
                          <>
                            <strong>📍 {place.name}</strong>
                            <div>ID: {place.id}</div>
                            <div>Тип: {place.type}</div>
                            <div>Радиус (из тэга): {r ? `${r} м` : '—'}</div>
                            <button
                              onClick={() => {
                                setEditingPlace(place);
                                setPlaceError(null);
                                setShowEditPlace(true);
                              }}
                              className="selection-popup-action"
                            >
                              ✏️ Редактировать
                            </button>
                          </>
                        );
                      })()}
                    </div>
                  )}
                  {selectedNode && graphState.graphData && (
                    <div className="selection-info">
                      <strong>Узел #{selectedNode}</strong>
                      {(() => {
                        const node = graphState.graphData.nodes.find(n => n.id === selectedNode);
                        return node ? (
                          <>
                            <div>Тип: {node.node_type === 'road' ? 'Дорога' : node.node_type === 'ladder' ? 'Лестница' : 'Перекресток'}</div>
                            <div>X: {node.x.toFixed(6)}, Y: {node.y.toFixed(6)}, Z: {node.z.toFixed(1)}</div>
                            <button
                              onClick={() => {
                                setEditingNode(node);
                                setNodeError(null);
                                setShowEditNode(true);
                              }}
                              className="selection-popup-action"
                            >
                              ✏️ Редактировать
                            </button>
                          </>
                        ) : null;
                      })()}
                    </div>
                  )}
                  {selectedEdge && graphState.graphData && (
                    <div className="selection-info">
                      <strong>Ребро #{selectedEdge}</strong>
                      {(() => {
                        const edge = graphState.graphData.edges.find(e => e.id === selectedEdge);
                        if (!edge) return null;
                        const fromNode = graphState.graphData.nodes.find(n => n.id === edge.from_node_id);
                        const toNode = graphState.graphData.nodes.find(n => n.id === edge.to_node_id);
                        return (
                          <>
                            <div>Тип: {edge.edge_type === 'vertical' ? 'Лестница (вертикальное)' : edge.edge_type === 'ladder' ? 'Лестница' : 'Горизонтальное'}</div>
                            <div>От узла #{edge.from_node_id} → К узлу #{edge.to_node_id}</div>
                            {fromNode && toNode && (
                              <div>Длина: {Math.sqrt((toNode.x - fromNode.x) ** 2 + (toNode.y - fromNode.y) ** 2).toFixed(1)} м</div>
                            )}
                            <button
                              onClick={() => {
                                setEditingEdge(edge);
                                setEdgeError(null);
                                setShowEditEdge(true);
                              }}
                              className="selection-popup-action"
                            >
                              ✏️ Редактировать
                            </button>
                          </>
                        );
                      })()}
                    </div>
                  )}
                  {selectedTag && graphState.graphData && (
                    <div className="selection-info">
                      <strong>📍 {(() => {
                        const tag = graphState.graphData.tags.find(t => t.id === selectedTag);
                        return tag ? tag.name : `Метка #${selectedTag}`;
                      })()}</strong>
                      {(() => {
                        const tag = graphState.graphData.tags.find(t => t.id === selectedTag);
                        return tag ? (
                          <>
                            <div>Тип: {tag.point_type}</div>
                            {tag.beacon_id && <div>ID метки: {tag.beacon_id}</div>}
                            {tag.beacon_mac && <div>MAC адрес: {tag.beacon_mac}</div>}
                            {tag.beacon_place && <div>Место установки: {tag.beacon_place}</div>}
                            {tag.battery_level !== null && tag.battery_level !== undefined && (
                              <div>Уровень заряда: {tag.battery_level.toFixed(1)}%</div>
                            )}
                            {tag.battery_updated_at && (
                              <div>Дата изменения заряда: {new Date(tag.battery_updated_at).toLocaleString('ru-RU')}</div>
                            )}
                            <div>Радиус: {tag.radius} м</div>
                            {(() => {
                              const lonLatFromPlace = tag.place ? getPlaceLonLat(tag.place) : null;
                              const lon = lonLatFromPlace?.lon ?? tag.x ?? 0;
                              const lat = lonLatFromPlace?.lat ?? tag.y ?? 0;
                              const z = tag.z ?? 0;
                              return (
                                <div>
                                  Позиция: ({lon.toFixed(6)}, {lat.toFixed(6)}, {z.toFixed(1)})
                                </div>
                              );
                            })()}
                            <button
                              onClick={() => {
                                setEditingTag(tag);
                                setTagError(null);
                                setShowEditTag(true);
                              }}
                              className="selection-popup-action"
                            >
                              ✏️ Редактировать
                            </button>
                          </>
                        ) : null;
                      })()}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Попап редактирования узла в правом верхнем углу */}
            {showEditNode && editingNode && (
              <div className="edit-popup" role="dialog">
                <div className="edit-popup-header">
                  <h3>Редактировать узел #{editingNode.id}</h3>
                  <button className="edit-popup-close" onClick={() => setShowEditNode(false)}>&times;</button>
                </div>
                <div className="edit-popup-body">
                  <div className="form-group">
                    <label>Database ID:</label>
                    <input
                      type="number"
                      value={editingNode.id}
                      disabled
                      style={{ backgroundColor: COLOR_BG_SURFACE, color: COLOR_MUTED, cursor: 'not-allowed', border: '1px solid var(--color-border)' }}
                      title="ID узла в базе данных (только для чтения)"
                    />
                  </div>
                  <div className="form-group">
                    <label>Тип узла:</label>
                    <select
                      value={editingNode.node_type}
                      onChange={(e) => setEditingNode({...editingNode, node_type: e.target.value})}
                    >
                      <option value="road">Дорога</option>
                      <option value="intersection">Перекресток</option>
                      <option value="ladder">Лестница</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Координата X (Longitude/Долгота):</label>
                    <input
                      type="number"
                      step="0.000001"
                      value={editingNode.x}
                      onChange={(e) => setEditingNode({...editingNode, x: parseFloat(e.target.value)})}
                    />
                  </div>
                  <div className="form-group">
                    <label>Координата Y (Latitude/Широта):</label>
                    <input
                      type="number"
                      step="0.000001"
                      value={editingNode.y}
                      onChange={(e) => setEditingNode({...editingNode, y: parseFloat(e.target.value)})}
                    />
                  </div>
                  {nodeError && (
                    <div className="error-message" style={{
                      backgroundColor: 'rgba(209, 92, 41, 0.18)',
                      border: '1px solid rgba(209, 92, 41, 0.35)',
                      borderRadius: '6px',
                      padding: '12px',
                      margin: '12px 0',
                      color: COLOR_ACCENT,
                      fontSize: '14px'
                    }}>
                      <strong>Ошибка:</strong> {nodeError}
                    </div>
                  )}
                </div>
                <div className="edit-popup-footer">
                  <button onClick={() => setShowEditNode(false)}>Отмена</button>
                  <button onClick={async () => {
                    if (!editingNode || !graphState.selectedHorizon) return;
                    
                    setNodeError(null);
                    
                      try {
                      const response = await fetch(`/api/nodes/${editingNode.id}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          x: editingNode.x,
                          y: editingNode.y,
                          node_type: editingNode.node_type
                          // z не отправляем - это readonly поле, вычисляется из horizon.height
                        })
                      });
                      
                      if (response.ok) {
                        graphState.loadGraphData(graphState.selectedHorizon.id);
                        setShowEditNode(false);
                        setEditingNode(null);
                        setNodeError(null);
                      } else {
                        const errorData = await response.json();
                        const errorMessage = errorData.error || errorData.detail || 'Ошибка при обновлении узла';
                        setNodeError(errorMessage);
                        console.error('Error updating node:', errorData);
                      }
                    } catch (error) {
                      const message = error instanceof Error ? error.message : 'Неизвестная ошибка';
                      setNodeError(`Ошибка сети: ${message}`);
                      console.error('Error updating node:', error);
                    }
                  }} className="btn-primary">Сохранить</button>
                </div>
              </div>
            )}

            {/* Попап редактирования места в правом верхнем углу */}
            {showEditPlace && editingPlace && (
              <div className="edit-popup" role="dialog">
                <div className="edit-popup-header">
                  <h3>Редактировать место #{editingPlace.id}</h3>
                  <button className="edit-popup-close" onClick={() => setShowEditPlace(false)}>&times;</button>
                </div>
                <div className="edit-popup-body">
                  <div className="form-group">
                    <label>Database ID:</label>
                    <input
                      type="number"
                      value={editingPlace.id}
                      disabled
                      style={{ backgroundColor: COLOR_BG_SURFACE, color: COLOR_MUTED, cursor: 'not-allowed', border: '1px solid var(--color-border)' }}
                      title="ID места в базе данных (только для чтения)"
                    />
                  </div>
                  <div className="form-group">
                    <label>Название места:</label>
                    <input
                      type="text"
                      value={editingPlace.name}
                      onChange={(e) => setEditingPlace({ ...editingPlace, name: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>Тип места:</label>
                    <select
                      value={editingPlace.type}
                      onChange={(e) => setEditingPlace({ ...editingPlace, type: e.target.value })}
                    >
                      <option value="transit">Транзитное место</option>
                      <option value="load">Место погрузки</option>
                      <option value="reload">Место перегрузки</option>
                      <option value="unload">Место разгрузки</option>
                      <option value="park">Место стоянки</option>
                    </select>
                  </div>
                  {graphState.graphData && (
                    (() => {
                      const linkedTag = graphState.graphData.tags.find(t => t.place_id === editingPlace.id);
                      if (!linkedTag) return null;
                      return (
                        <div className="form-group">
                          <label>Связанная метка:</label>
                          <div style={{ fontSize: '13px', color: 'var(--color-text-muted)', marginBottom: '6px' }}>
                            Метка #{linkedTag.id}, радиус: {linkedTag.radius || 25} м
                          </div>
                          <button
                            type="button"
                            className="selection-popup-action"
                            onClick={() => {
                              setEditingTag(linkedTag);
                              setTagError(null);
                              setShowEditTag(true);
                              setShowEditPlace(false);
                            }}
                          >
                            ✏️ Редактировать метку (радиус)
                          </button>
                        </div>
                      );
                    })()
                  )}
                  {placeError && (
                    <div
                      className="error-message"
                      style={{
                        backgroundColor: 'rgba(209, 92, 41, 0.18)',
                        border: '1px solid rgba(209, 92, 41, 0.35)',
                        borderRadius: '6px',
                        padding: '12px',
                        margin: '12px 0',
                        color: COLOR_ACCENT,
                        fontSize: '14px',
                      }}
                    >
                      <strong>Ошибка:</strong> {placeError}
                    </div>
                  )}
                </div>
                <div className="edit-popup-footer">
                  <button onClick={() => setShowEditPlace(false)}>Отмена</button>
                  <button onClick={handleUpdatePlace} className="btn-primary">Сохранить</button>
                </div>
              </div>
            )}

            {/* Попап редактирования метки в правом верхнем углу */}
            {showEditTag && editingTag && (
              <div className="edit-popup" role="dialog">
                <div className="edit-popup-header">
                  <h3>Редактировать метку #{editingTag.id}</h3>
                  <button className="edit-popup-close" onClick={() => setShowEditTag(false)}>&times;</button>
                </div>
                <div className="edit-popup-body">
                  <div className="form-group">
                    <label>Database ID:</label>
                    <input
                      type="number"
                      value={editingTag.id}
                      disabled
                      style={{ backgroundColor: COLOR_BG_SURFACE, color: COLOR_MUTED, cursor: 'not-allowed', border: '1px solid var(--color-border)' }}
                      title="ID метки в базе данных (только для чтения)"
                    />
                  </div>
                  <div className="form-group">
                    <label>ID метки (beacon_id):</label>
                    <input
                      type="text"
                      placeholder="Уникальная ID метки"
                      value={editingTag.beacon_id || editingTag.point_id || ''}
                      onChange={(e) => setEditingTag({
                        ...editingTag,
                        beacon_id: e.target.value,
                        point_id: e.target.value  // Обратная совместимость
                      })}
                    />
                    <small style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '4px', display: 'block' }}>
                      Уникальная ID метки для идентификации другими устройствами
                    </small>
                  </div>
                  <div className="form-group">
                    <label>MAC адрес (beacon_mac):</label>
                    <input
                      type="text"
                      placeholder="XX:XX:XX:XX:XX:XX"
                      value={editingTag.beacon_mac || ''}
                      onChange={(e) => setEditingTag({...editingTag, beacon_mac: e.target.value})}
                    />
                    <small style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '4px', display: 'block' }}>
                      Формат: XX:XX:XX:XX:XX:XX или XX-XX-XX-XX-XX-XX
                    </small>
                  </div>
                  {/* Поле "Место установки" временно скрыто */}
                  {/* <div className="form-group">
                    <label>Место установки (beacon_place):</label>
                    <select
                      value={editingTag.beacon_place || ''}
                      onChange={(e) => setEditingTag({...editingTag, beacon_place: e.target.value})}
                    >
                      <option value="">Выберите место установки</option>
                      <option value="Шахта №1, горизонт -50м">Шахта №1, горизонт -50м</option>
                      <option value="Шахта №1, горизонт -100м">Шахта №1, горизонт -100м</option>
                      <option value="Шахта №2, горизонт -50м">Шахта №2, горизонт -50м</option>
                      <option value="Шахта №2, горизонт -100м">Шахта №2, горизонт -100м</option>
                    </select>
                    <small style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '4px', display: 'block' }}>
                      Привязка метки к конкретному пункту установки
                    </small>
                  </div> */}
                  <div className="form-group">
                    <label>Уровень заряда (beacon_power):</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.1"
                      placeholder="0-100"
                      value={editingTag.battery_level ?? ''}
                      disabled
                      style={{ backgroundColor: COLOR_BG_SURFACE, color: COLOR_MUTED, cursor: 'not-allowed' }}
                    />
                    <small style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '4px', display: 'block' }}>
                      Заполняется автоматически, редактирование недоступно
                    </small>
                  </div>
                  {editingTag.battery_updated_at && (
                    <div className="form-group">
                      <label>Дата изменения уровня заряда:</label>
                      <div style={{ color: 'var(--color-text-muted)', fontSize: '13px' }}>
                        {new Date(editingTag.battery_updated_at).toLocaleString('ru-RU')}
                      </div>
                    </div>
                  )}
                  <div className="form-group">
                    <label>Название:</label>
                    <input
                      type="text"
                      value={editingTag.name}
                      onChange={(e) => setEditingTag({...editingTag, name: e.target.value})}
                    />
                  </div>
                  <div className="form-group">
                    <label>Тип метки (beacon_type):</label>
                    <select
                      value={editingTag.point_type}
                      onChange={(e) => setEditingTag({...editingTag, point_type: e.target.value})}
                    >
                      <option value="transit">Транзитное место</option>
                      <option value="loading">Место погрузки</option>
                      <option value="transfer">Место перегрузки</option>
                      <option value="unloading">Место разгрузки</option>
                      <option value="transport">Место стоянки</option>
                    </select>
                    <small style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '4px', display: 'block' }}>
                      Согласно типу метки, она будет участвовать в алгоритмах рейсов
                    </small>
                  </div>
                  <div className="form-group">
                    <label>Местоположение (координата X) - beacon_placement:</label>
                    <input
                      type="number"
                      step="0.000001"
                      value={editingTag.x}
                      onChange={(e) => setEditingTag({...editingTag, x: parseFloat(e.target.value)})}
                    />
                    <small style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '4px', display: 'block' }}>
                      Longitude/Долгота - указание места установки метки на карте
                    </small>
                  </div>
                  <div className="form-group">
                    <label>Местоположение (координата Y) - beacon_placement:</label>
                    <input
                      type="number"
                      step="0.000001"
                      value={editingTag.y}
                      onChange={(e) => setEditingTag({...editingTag, y: parseFloat(e.target.value)})}
                    />
                    <small style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '4px', display: 'block' }}>
                      Latitude/Широта - указание места установки метки на карте
                    </small>
                  </div>
                  <div className="form-group">
                    <label>Радиус действия (beacon_radius): {editingTag.radius} м</label>
                    <input
                      type="range"
                      min="10"
                      max="100"
                      step="1"
                      value={editingTag.radius}
                      onChange={(e) => {
                        const newRadius = parseFloat(e.target.value);
                        setEditingTag({
                          ...editingTag,
                          radius: newRadius
                        });
                      }}
                      style={{ width: '100%' }}
                    />
                    <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                      <input
                        type="number"
                        min="10"
                        max="100"
                        value={editingTag.radius}
                        onChange={(e) => {
                          const newRadius = Math.min(100, Math.max(10, parseFloat(e.target.value) || 25));
                          setEditingTag({
                            ...editingTag,
                            radius: newRadius
                          });
                        }}
                        style={{ flex: 1 }}
                      />
                    </div>
                  </div>
                  {tagError && (
                    <div className="error-message" style={{
                      backgroundColor: 'rgba(209, 92, 41, 0.18)',
                      border: '1px solid rgba(209, 92, 41, 0.35)',
                      borderRadius: '6px',
                      padding: '12px',
                      margin: '12px 0',
                      color: COLOR_ACCENT,
                      fontSize: '14px'
                    }}>
                      <strong>Ошибка:</strong> {tagError}
                    </div>
                  )}
                </div>
                <div className="edit-popup-footer">
                  <button onClick={() => setShowEditTag(false)}>Отмена</button>
                  <button onClick={handleUpdateTag} className="btn-primary">Сохранить</button>
                </div>
              </div>
            )}

            {/* Попап редактирования ребра в правом верхнем углу */}
            {showEditEdge && editingEdge && (
              <div className="edit-popup" role="dialog">
                <div className="edit-popup-header">
                  <h3>Редактировать ребро #{editingEdge.id}</h3>
                  <button className="edit-popup-close" onClick={() => setShowEditEdge(false)}>&times;</button>
                </div>
                <div className="edit-popup-body">
                  <div className="form-group">
                    <label>Database ID:</label>
                    <input
                      type="number"
                      value={editingEdge.id}
                      disabled
                      style={{ backgroundColor: COLOR_BG_SURFACE, color: COLOR_MUTED, cursor: 'not-allowed', border: '1px solid var(--color-border)' }}
                      title="ID ребра в базе данных (только для чтения)"
                    />
                  </div>
                  <div className="form-group">
                    <label>Тип ребра:</label>
                    <select
                      value={editingEdge.edge_type || 'horizontal'}
                      onChange={(e) => setEditingEdge({...editingEdge, edge_type: e.target.value})}
                    >
                      <option value="horizontal">Горизонтальное</option>
                      <option value="vertical">Лестница (вертикальное)</option>
                      <option value="ladder">Лестница</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>От узла ID:</label>
                    <input
                      type="number"
                      value={editingEdge.from_node_id}
                      onChange={(e) => setEditingEdge({...editingEdge, from_node_id: parseInt(e.target.value)})}
                    />
                  </div>
                  <div className="form-group">
                    <label>К узлу ID:</label>
                    <input
                      type="number"
                      value={editingEdge.to_node_id}
                      onChange={(e) => setEditingEdge({...editingEdge, to_node_id: parseInt(e.target.value)})}
                    />
                  </div>
                  <div className="form-group">
                    <label>Вес (опционально):</label>
                    <input
                      type="number"
                      step="0.1"
                      value={editingEdge.weight || ''}
                      placeholder="Автоматически рассчитается если не указано"
                      onChange={(e) => setEditingEdge({...editingEdge, weight: e.target.value ? parseFloat(e.target.value) : undefined})}
                    />
                  </div>
                  {edgeError && (
                    <div className="error-message" style={{
                      backgroundColor: 'rgba(209, 92, 41, 0.18)',
                      border: '1px solid rgba(209, 92, 41, 0.35)',
                      borderRadius: '6px',
                      padding: '12px',
                      margin: '12px 0',
                      color: COLOR_ACCENT,
                      fontSize: '14px'
                    }}>
                      <strong>Ошибка:</strong> {edgeError}
                    </div>
                  )}
                </div>
                <div className="edit-popup-footer">
                  <button onClick={() => setShowEditEdge(false)}>Отмена</button>
                  <button onClick={async () => {
                    if (!editingEdge || !graphState.selectedHorizon) return;
                    
                    setEdgeError(null);
                    
                    try {
                      const response = await fetch(`/api/edges/${editingEdge.id}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          from_node_id: editingEdge.from_node_id,
                          to_node_id: editingEdge.to_node_id,
                          edge_type: editingEdge.edge_type,
                          weight: editingEdge.weight
                        })
                      });
                      
                      if (response.ok) {
                        graphState.loadGraphData(graphState.selectedHorizon.id);
                        setShowEditEdge(false);
                        setEditingEdge(null);
                        setEdgeError(null);
                      } else {
                        const errorData = await response.json();
                        const errorMessage = errorData.error || errorData.detail || 'Ошибка при обновлении ребра';
                        setEdgeError(errorMessage);
                        console.error('Error updating edge:', errorData);
                      }
                    } catch (error) {
                      const message = error instanceof Error ? error.message : 'Неизвестная ошибка';
                      setEdgeError(`Ошибка сети: ${message}`);
                      console.error('Error updating edge:', error);
                    }
                  }} className="btn-primary">Сохранить</button>
                </div>
              </div>
            )}
          </div>

          <div className="right-dock">
            <div className="dock-buttons">
              <button
                type="button"
                className={`dock-button ${isVehiclesPanelOpen ? 'active' : ''}`}
                onClick={() => setIsVehiclesPanelOpen(prev => !prev)}
                title={isVehiclesPanelOpen ? 'Скрыть панель транспорта' : 'Показать панель транспорта'}
                aria-pressed={isVehiclesPanelOpen}
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
            {isVehiclesPanelOpen && (
              <aside
                className="side-panel right open"
                style={rightPanelStyle}
              >
                <div className="panel-shell">
                  <div className="panel-header-row">
                    <div className="panel-title-group">
                      <h2 className="panel-title">Транспорт</h2>
                      <span className="panel-title-count">{Object.keys(vehicles).length}</span>
                    </div>
                    <button
                      type="button"
                      className="panel-toggle-inline"
                      onClick={() => setIsVehiclesPanelOpen(false)}
                      title="Скрыть панель"
                    >
                      <span aria-hidden="true">—</span>
                      <span className="sr-only">Скрыть панель</span>
                    </button>
                  </div>
                  <div className={`panel-body visible`}>
                    <div className="panel-scroll">
                      {Object.keys(vehicles).length > 0 ? (
                        <VehiclesPanel
                          vehicles={Object.fromEntries(
                            Object.entries(vehicles).map(([id, vehicle]) => [
                              id,
                              {
                                ...vehicle,
                                name: vehicle.name || vehicleNamesMapRef.current.get(id) || vehicle.vehicle_id
                              }
                            ])
                          )}
                          onVehicleClick={centerOnVehicle}
                          horizons={graphState.horizons}
                          isOpen={isVehiclesPanelOpen}
                        />
                      ) : (
                        <div className="panel-empty">Нет данных о транспорте</div>
                      )}
                    </div>
                  </div>
                </div>
              </aside>
            )}
          </div>
        </div>
      )}

      {/* Переключатель координат СКРЫТ - не нужен в продакшене */}
      {/* {currentView === 'editor' && (
        <div className="coords-toggle">
          <label>
            <input
              type="checkbox"
              checked={showCoordinates}
              onChange={(e) => setShowCoordinates(e.target.checked)}
            />
            Показать координаты
          </label>
          {showCoordinates && cursorPos && (
            <div className="coords-display">
              X: {cursorPos.x.toFixed(1)}, Y: {cursorPos.y.toFixed(1)}
            </div>
          )}
        </div>
      )} */}

      {/* Диалог импорта графа */}
      <ImportDialog
        isOpen={showImportDialog}
        onClose={() => setShowImportDialog(false)}
        onImportSuccess={handleImportSuccess}
      />

      {/* Диалог создания лестницы */}
      <LadderDialog
        isOpen={showLadderDialog}
        sourceNode={ladderSourceNode}
        sourceHorizon={graphState.selectedHorizon}
        availableHorizons={graphState.horizons}
        onConfirm={handleLadderConfirm}
        onConfirmTwoLevels={handleLadderConfirmTwoLevels}
        onCancel={handleLadderCancel}
        mode={ladderStep === 'selectLevels' ? 'selectTwoLevels' : 'selectTargetLevel'}
      />


      {/* Модальное окно редактирования лестницы */}
      {showEditLadder && editingLadderNode && graphState.graphData && (
        <div className="modal-overlay">
          <div className="modal" style={{ maxWidth: '500px' }}>
            <div className="modal-header">
              <h3>🪜 Редактировать лестницу</h3>
              <button onClick={() => {
                setShowEditLadder(false);
                setEditingLadderNode(null);
                setLadderConnectedNodes([]);
              }}>&times;</button>
            </div>
            <div className="modal-body">
              {loadingLadderConnections ? (
                <div style={{ padding: '20px', textAlign: 'center', color: COLOR_MUTED }}>
                  Загрузка информации о лестнице...
                </div>
              ) : (() => {
                // Определяем горизонты и узлы
                const horizon1 = graphState.horizons.find(h => h.id === editingLadderNode.horizon_id);
                const node1 = editingLadderNode;
                
                // Берем первый связанный узел (лестница обычно соединяет два уровня)
                const firstConnection = ladderConnectedNodes[0];
                const horizon2 = firstConnection?.horizon;
                const node2 = firstConnection?.node;
                const ladderEdge = firstConnection?.edge;
                
                if (!firstConnection) {
                  return (
                    <div style={{ padding: '12px', color: COLOR_MUTED, fontStyle: 'italic', textAlign: 'center' }}>
                      Нет связанных узлов. Лестница не соединена с другими уровнями.
                    </div>
                  );
                }

                return (
                  <>
                    {/* ID лестницы */}
                    <div className="form-group">
                      <label>ID лестницы:</label>
                      <input
                        type="number"
                        value={ladderEdge.id}
                        disabled
                        style={{ backgroundColor: COLOR_BG_SURFACE, color: COLOR_MUTED, cursor: 'not-allowed', border: '1px solid var(--color-border)' }}
                        title="ID ребра лестницы (только для чтения)"
                      />
                    </div>

                    {/* Горизонт 1 */}
                    <div className="form-group">
                      <label>Горизонт 1:</label>
                      <input
                        type="text"
                        value={horizon1 ? `${horizon1.name} (${horizon1.height}м)` : `Уровень ${editingLadderNode.horizon_id}`}
                        disabled
                        style={{ backgroundColor: COLOR_BG_SURFACE, color: COLOR_MUTED, cursor: 'not-allowed', border: '1px solid var(--color-border)' }}
                      />
                    </div>

                    {/* Горизонт 2 */}
                    <div className="form-group">
                      <label>Горизонт 2:</label>
                      <input
                        type="text"
                        value={horizon2 ? `${horizon2.name} (${horizon2.height}м)` : 'Не найден'}
                        disabled
                        style={{ backgroundColor: COLOR_BG_SURFACE, color: COLOR_MUTED, cursor: 'not-allowed', border: '1px solid var(--color-border)' }}
                      />
                    </div>

                    {/* Узел 1 */}
                    <div className="form-group">
                      <label>Узел 1:</label>
                      <input
                        type="text"
                        value={`ID: ${node1.id} | Координаты: (${node1.x.toFixed(6)}, ${node1.y.toFixed(6)})`}
                        disabled
                        style={{ backgroundColor: COLOR_BG_SURFACE, color: COLOR_MUTED, cursor: 'not-allowed', border: '1px solid var(--color-border)' }}
                      />
                    </div>

                    {/* Узел 2 */}
                    <div className="form-group">
                      <label>Узел 2:</label>
                      <input
                        type="text"
                        value={node2 ? `ID: ${node2.id} | Координаты: (${node2.x.toFixed(6)}, ${node2.y.toFixed(6)})` : 'Не найден'}
                        disabled
                        style={{ backgroundColor: COLOR_BG_SURFACE, color: COLOR_MUTED, cursor: 'not-allowed', border: '1px solid var(--color-border)' }}
                      />
                    </div>
                  </>
                );
              })()}
            </div>
            <div className="modal-footer">
              <button onClick={() => {
                setShowEditLadder(false);
                setEditingLadderNode(null);
                setLadderConnectedNodes([]);
              }}>Закрыть</button>
              {ladderConnectedNodes.length > 0 && (() => {
                const firstConnection = ladderConnectedNodes[0];
                const ladderEdge = firstConnection?.edge;
                if (!ladderEdge) return null;
                
                return (
                  <button
                    onClick={async () => {
                      if (window.confirm(`Удалить лестницу?\n\nЭто удалит связь между уровнями "${graphState.horizons.find(h => h.id === editingLadderNode.horizon_id)?.name}" и "${firstConnection.horizon.name}".`)) {
                        try {
                          const response = await fetch(`/api/edges/${ladderEdge.id}`, {
                            method: 'DELETE'
                          });
                          if (response.ok) {
                            // Перезагружаем данные на обоих горизонтах, если это вертикальное ребро
                            const currentHorizonId = graphState.selectedHorizon?.id || editingLadderNode.horizon_id;
                            await graphState.loadGraphData(currentHorizonId);
                            
                            // Если есть связанный узел на другом горизонте, перезагружаем и его
                            if (firstConnection && firstConnection.horizon.id !== currentHorizonId) {
                              await graphState.loadGraphData(firstConnection.horizon.id);
                            }
                            
                            setShowEditLadder(false);
                            setEditingLadderNode(null);
                            setLadderConnectedNodes([]);
                            alert('Лестница удалена');
                          } else {
                            const errorData = await response.json();
                            alert(`Ошибка: ${errorData.error || 'Не удалось удалить лестницу'}`);
                          }
                        } catch (error) {
                          console.error('Error deleting ladder edge:', error);
                          alert('Ошибка при удалении лестницы');
                        }
                      }
                    }}
                    className="btn-primary"
                    style={{
                      backgroundColor: 'rgba(209, 92, 41, 0.8)',
                      border: '1px solid rgba(209, 92, 41, 1)',
                      color: COLOR_LIGHT
                    }}
                  >
                    Удалить лестницу
                  </button>
                );
              })()}
            </div>
          </div>
        </div>
      )}

      {isHorizonsModalOpen && (
        <div className="modal-overlay" role="presentation">
          <div className="modal horizons-modal" role="dialog" aria-modal="true">
            <div className="modal-header">
              <h3>Горизонты и содержимое</h3>
              <button onClick={handleCloseHorizonsModal} aria-label="Закрыть">&times;</button>
            </div>
            <div className="modal-body">
              {isHorizonsModalLoading && (
                <div className="modal-loading">Загрузка данных...</div>
              )}
              {horizonsModalError && (
                <div className="modal-error">{horizonsModalError}</div>
              )}
              {!isHorizonsModalLoading && !horizonsModalError && (
                <div className="horizon-accordion">
                  {!Array.isArray(graphState.horizons) || graphState.horizons.length === 0 ? (
                    <div className="modal-empty">Горизонты отсутствуют</div>
                  ) : (
                    graphState.horizons.map(horizon => {
                      const details = horizonDetails ? horizonDetails[horizon.id] : null;
                      const isExpanded = expandedHorizons.includes(horizon.id);
                      return (
                        <div className={`horizon-accordion-item ${isExpanded ? 'expanded' : ''}`} key={horizon.id}>
                          <button
                            type="button"
                            className="horizon-accordion-trigger"
                            onClick={() => toggleHorizonExpanded(horizon.id)}
                          >
                            <div className="horizon-accordion-title">
                              <span className="horizon-name">{horizon.name}</span>
                              <span className="horizon-meta">Высота: {horizon.height} м</span>
                            </div>
                            <div className="horizon-counts">
                              <span>{details ? details.nodes.length : '...'} узлов</span>
                              <span>{details ? (details.places?.length ?? 0) : '...'} мест</span>
                              <span>{details ? details.edges.filter(e => e.edge_type === 'vertical').length : '...'} лестниц</span>
                            </div>
                            <span className="horizon-chevron" aria-hidden="true">{isExpanded ? '▲' : '▼'}</span>
                          </button>
                          {isExpanded && (
                            <div className="horizon-accordion-content">
                              {!details && (
                                <div className="horizon-subsection horizon-subsection-empty">Данные загружаются...</div>
                              )}
                              {details && (
                                <>
                                  <div className="horizon-subsection">
                                    <h4>Узлы</h4>
                                    {details.nodes.length === 0 ? (
                                      <p className="horizon-subsection-empty">Узлов нет</p>
                                    ) : (
                                      <ul className="horizon-list">
                                        {details.nodes.map(node => (
                                          <li key={node.id} className="horizon-node-item">
                                            <div className="horizon-node-header">
                                              <strong>#{node.id}</strong>
                                            </div>
                                            <div className="horizon-node-details">
                                              <div className="horizon-node-field">
                                                <span className="horizon-node-label">Местоположение (координата):</span>
                                                <button
                                                  className="horizon-node-coordinate-link"
                                                  onClick={(e) => {
                                                    e.preventDefault();
                                                    e.stopPropagation();
                                                    showNodeOnMap(node);
                                                  }}
                                                  title="Кликните, чтобы показать на карте и центрировать камеру"
                                                >
                                                  ({node.x.toFixed(3)}, {node.y.toFixed(3)}, {node.z.toFixed(1)})
                                                </button>
                                              </div>
                                              <div className="horizon-node-field">
                                                <span className="horizon-node-label">Тип узла:</span>
                                                <span className="horizon-node-value">{node.node_type || '—'}</span>
                                              </div>
                                            </div>
                                          </li>
                                        ))}
                                      </ul>
                                    )}
                                  </div>
                                  <div className="horizon-subsection">
                                    <h4>Места</h4>
                                    {(!details.places || details.places.length === 0) ? (
                                      <p className="horizon-subsection-empty">Мест нет</p>
                                    ) : (
                                      <ul className="horizon-list horizon-tags-list">
                                        {details.places.map(place => {
                                          const xy = getPlaceCanvasXY(place, settings.transformGPStoCanvas);
                                          const coordText = xy ? `(${xy.x.toFixed(1)}, ${xy.y.toFixed(1)})` : '(—)';
                                          return (
                                            <li key={place.id} className="horizon-tag-item">
                                              <div className="horizon-tag-header">
                                                <strong>{place.name}</strong>
                                              </div>
                                              <div className="horizon-tag-details">
                                                <div className="horizon-tag-field">
                                                  <span className="horizon-tag-label">ID:</span>
                                                  <span className="horizon-tag-value">{place.id}</span>
                                                </div>
                                                <div className="horizon-tag-field">
                                                  <span className="horizon-tag-label">Тип:</span>
                                                  <span className="horizon-tag-value">{place.type}</span>
                                                </div>
                                                <div className="horizon-tag-field">
                                                  <span className="horizon-tag-label">Координаты:</span>
                                                  <button
                                                    className="horizon-tag-coordinate-link"
                                                    onClick={(e) => {
                                                      e.preventDefault();
                                                      e.stopPropagation();
                                                      showPlaceOnMap(place);
                                                    }}
                                                    title="Кликните, чтобы показать на карте и центрировать камеру"
                                                    disabled={!xy}
                                                    style={!xy ? { opacity: 0.6, cursor: 'not-allowed' } : undefined}
                                                  >
                                                    {coordText}
                                                  </button>
                                                </div>
                                                <div className="horizon-tag-field">
                                                  <span className="horizon-tag-label">Радиус (из тэга):</span>
                                                  <span className="horizon-tag-value">
                                                    {(() => {
                                                      const rs = (details.tags || [])
                                                        .filter((t) => t.place_id === place.id)
                                                        .map((t) => t.radius || 25);
                                                      const r = rs.length ? Math.max(...rs) : null;
                                                      return r ? `${r} м` : '—';
                                                    })()}
                                                  </span>
                                                </div>
                                              </div>
                                            </li>
                                          );
                                        })}
                                      </ul>
                                    )}
                                  </div>
                                  <div className="horizon-subsection">
                                    <h4>Теги (телеметрия)</h4>
                                    {details.tags.length === 0 ? (
                                      <p className="horizon-subsection-empty">Тегов нет</p>
                                    ) : (
                                      <ul className="horizon-list horizon-tags-list">
                                        {details.tags.map(tag => (
                                          <li key={tag.id} className="horizon-tag-item">
                                            <div className="horizon-tag-header">
                                              <strong>{tag.tag_id || tag.beacon_id || tag.point_id || `Tag #${tag.id}`}</strong>
                                            </div>
                                            <div className="horizon-tag-details">
                                              <div className="horizon-tag-field">
                                                <span className="horizon-tag-label">DB ID:</span>
                                                <span className="horizon-tag-value">{tag.id}</span>
                                              </div>
                                              <div className="horizon-tag-field">
                                                <span className="horizon-tag-label">MAC:</span>
                                                <span className="horizon-tag-value">{tag.tag_mac || tag.beacon_mac || '—'}</span>
                                              </div>
                                              <div className="horizon-tag-field">
                                                <span className="horizon-tag-label">Battery:</span>
                                                <span className="horizon-tag-value">
                                                  {tag.battery_level !== null && tag.battery_level !== undefined
                                                    ? `${tag.battery_level.toFixed(0)}%`
                                                    : '—'}
                                                </span>
                                              </div>
                                              {tag.battery_updated_at && (
                                                <div className="horizon-tag-field">
                                                  <span className="horizon-tag-label">Battery updated:</span>
                                                  <span className="horizon-tag-value">{new Date(tag.battery_updated_at).toLocaleString('ru-RU')}</span>
                                                </div>
                                              )}
                                            </div>
                                          </li>
                                        ))}
                                      </ul>
                                    )}
                                  </div>
                                  <div className="horizon-subsection">
                                    <h4>Лестницы</h4>
                                    {(() => {
                                      const ladderEdges = details.edges.filter(e => e.edge_type === 'vertical');
                                      if (ladderEdges.length === 0) {
                                        return <p className="horizon-subsection-empty">Лестниц нет</p>;
                                      }
                                      return (
                                        <ul className="horizon-list">
                                          {ladderEdges.map(edge => {
                                            // Находим узлы - один должен быть на текущем горизонте
                                            const fromNode = details.nodes.find(n => n.id === edge.from_node_id);
                                            const toNode = details.nodes.find(n => n.id === edge.to_node_id);
                                            
                                            // Определяем, какой узел на текущем горизонте
                                            const currentNode = fromNode && fromNode.horizon_id === horizon.id 
                                              ? fromNode 
                                              : toNode && toNode.horizon_id === horizon.id 
                                              ? toNode 
                                              : null;
                                            
                                            // Определяем связанный узел (на другом горизонте)
                                            const connectedNodeId = currentNode?.id === edge.from_node_id 
                                              ? edge.to_node_id 
                                              : edge.from_node_id;
                                            
                                            // Пытаемся найти связанный узел в данных других горизонтов
                                            const connectedNodeDetails = horizonDetails 
                                              ? Object.values(horizonDetails).find(d => 
                                                  d.nodes.some(n => n.id === connectedNodeId)
                                                )
                                              : null;
                                            const connectedNode = connectedNodeDetails?.nodes.find(n => n.id === connectedNodeId);
                                            const connectedHorizon = connectedNode 
                                              ? graphState.horizons.find(h => h.id === connectedNode.horizon_id)
                                              : null;
                                            
                                            return (
                                              <li key={edge.id} className="horizon-ladder-item">
                                                <div className="horizon-ladder-header">
                                                  <strong>Лестница #{edge.id}</strong>
                                                </div>
                                                <div className="horizon-ladder-details">
                                                  <div className="horizon-ladder-field">
                                                    <span className="horizon-ladder-label">Узел на текущем уровне:</span>
                                                    <span className="horizon-ladder-value">
                                                      {currentNode
                                                        ? `#${currentNode.id} (${currentNode.x.toFixed(3)}, ${currentNode.y.toFixed(3)})`
                                                        : '—'}
                                                    </span>
                                                  </div>
                                                  <div className="horizon-ladder-field">
                                                    <span className="horizon-ladder-label">Узел на связанном уровне:</span>
                                                    <span className="horizon-ladder-value">
                                                      {connectedNode && connectedHorizon
                                                        ? `#${connectedNode.id} на "${connectedHorizon.name}" (${connectedNode.x.toFixed(3)}, ${connectedNode.y.toFixed(3)})`
                                                        : `#${connectedNodeId} (данные не загружены)`}
                                                    </span>
                                                  </div>
                                                  <div className="horizon-ladder-field">
                                                    <span className="horizon-ladder-label">Соединяет уровни:</span>
                                                    <span className="horizon-ladder-value">
                                                      {currentNode && connectedHorizon
                                                        ? `${horizon.name} ↔ ${connectedHorizon.name}`
                                                        : currentNode
                                                        ? `${horizon.name} ↔ (уровень узла #${connectedNodeId})`
                                                        : '—'}
                                                    </span>
                                                  </div>
                                                </div>
                                              </li>
                                            );
                                          })}
                                        </ul>
                                      );
                                    })()}
                                  </div>
                                </>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GraphEditor;