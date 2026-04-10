/**
 * Хук для работы с данными графа через API
 */
import { useState, useEffect, useCallback } from 'react';
import { getHorizons, getHorizonGraph } from '../services/api';
import { Horizon, GraphData } from '../types/graph';

export function useGraphData() {
  const [horizons, setHorizons] = useState<Horizon[]>([]);
  const [selectedHorizon, setSelectedHorizon] = useState<Horizon | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);


  const loadHorizons = useCallback(async (): Promise<Horizon[]> => {
    setIsLoading(true);
    setError(null);
    let levelsData: Horizon[] = [];
    try {
      levelsData = await getHorizons();

      // Гарантируем, что levelsData всегда массив
      if (!Array.isArray(levelsData)) {
        console.error('getHorizons returned non-array:', typeof levelsData, levelsData);
        levelsData = [];
      }

      // Дополнительная проверка перед установкой состояния
      if (!Array.isArray(levelsData)) {
        console.error('levelsData is still not an array after check!');
        levelsData = [];
      }
      
      setHorizons(levelsData);

      // Автоматически выбираем первый уровень, если еще ничего не выбрано
      if (levelsData.length > 0 && !selectedHorizon) {
        setSelectedHorizon(levelsData[0]);
      }
    } catch (err) {
      console.error('Failed to load levels:', err);
      setHorizons([]); // В случае ошибки устанавливаем пустой массив
      setError('Не удалось загрузить горизонты');
    } finally {
      setIsLoading(false);
    }
    return levelsData;
  }, [selectedHorizon]);

  const loadGraphData = useCallback(async (levelId: number) => {
    try {
      setIsLoading(true);
      setError(null);
      // Инициализируем пустые данные сразу для моментального отображения
      setGraphData({
        nodes: [],
        edges: [],
        tags: [],
        places: [],
      });
      // Загружаем данные
      const data = await getHorizonGraph(levelId);
      setGraphData(data);
    } catch (err) {
      console.error('Failed to load graph data:', err);
      setError('Не удалось загрузить данные графа');
      // Устанавливаем пустые данные при ошибке
      setGraphData({
        nodes: [],
        edges: [],
        tags: [],
        places: [],
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshGraph = useCallback(() => {
    if (selectedHorizon) {
      loadGraphData(selectedHorizon.id);
    }
  }, [selectedHorizon, loadGraphData]);

  // Загрузка горизонтов при монтировании
  useEffect(() => {
    loadHorizons();
  }, []);

  // Загрузка графа при выборе горизонта
  useEffect(() => {
    if (selectedHorizon) {
      loadGraphData(selectedHorizon.id);
    }
  }, [selectedHorizon, loadGraphData]);

  const safeHorizons = Array.isArray(horizons) ? [...horizons] : [];

  return {
    horizons: safeHorizons, // Гарантируем, что всегда возвращаем массив
    selectedHorizon,
    graphData,
    isLoading,
    error,
    setSelectedHorizon,
    setGraphData,
    loadHorizons,
    loadGraphData,
    refreshGraph,
  };
}


