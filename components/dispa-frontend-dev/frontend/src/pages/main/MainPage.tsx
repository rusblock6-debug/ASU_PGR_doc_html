/**
 * Главная страница - информация о текущем рейсе и маршруте
 */
import { useEffect, useState, useCallback } from 'react';
import { tripServiceApi, Task, ActiveTrip } from '@/shared/api/tripServiceApi';
import { graphServiceApi } from '@/shared/api/graphServiceApi';
import './MainPage.css';

// API URL для SSE
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
// Vehicle ID (единый для всех SSE подключений)
const VEHICLE_ID = import.meta.env.VITE_VEHICLE_ID || '4_truck';

// Типы событий SSE
type StateTransitionEvent = {
  event_type: 'state_transition' | 'trip_completed';
  state?: string;
  vehicle_id?: string;
  cycle_id?: string | null;
  trip_id?: string | null;  // Опционально - только когда есть активный Trip
  task_id?: string | null;
  trigger_type?: string;
  point_id?: string | null;
  tag?: string | null;
  timestamp?: number;
  trip_type?: string; // Тип рейса (planned/unplanned)
  status?: string;
  unloading_point_id?: string | null;
  unloading_timestamp?: string;
};

type TagEvent = {
  point_id: string | null;
  point_type: string | null;
  timestamp: number;
};

type WeightEvent = {
  value?: number;
  status?: string;
  timestamp?: number;
};

export const MainPage = () => {
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [activeTrip, setActiveTrip] = useState<ActiveTrip | null>(null);
  const [completedTripsCount, setCompletedTripsCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Новые состояния для всегда видимого статуса
  const [currentState, setCurrentState] = useState<string>('idle');
  const [currentLocation, setCurrentLocation] = useState<string | null>(null);
  const [currentWeight, setCurrentWeight] = useState<number | null>(null);
  const [placesMap, setPlacesMap] = useState<Record<string, string>>({});
  const [currentTime, setCurrentTime] = useState<Date>(new Date());


  // Обработчик событий состояния из SSE
  const handleSSEEvent = useCallback((event: StateTransitionEvent) => {
    if (event.event_type === 'trip_completed') {
      // Рейс завершён - очищаем activeTrip и обновляем счётчики
      setActiveTrip(null);
      
      // Перезагружаем активное задание и счётчик рейсов
      tripServiceApi
        .getActiveTask()
        .then((task) => {
          if (task) {
            setActiveTask(task);
            // Обновляем счётчик рейсов
            return tripServiceApi.getCompletedTripsCount(task.task_id);
          }
          return 0;
        })
        .then((count) => {
          setCompletedTripsCount(count);
        })
        .catch((err) => {
          console.error('Failed to reload data after trip completion:', err);
        });
      
      return;
    }

    if (event.event_type === 'state_transition') {
      // Всегда обновляем текущий статус (даже если рейса нет)
      if (event.state) {
        setCurrentState(event.state);
      }
      
      // Если рейс завершен (нет trip_id в событии), очищаем activeTrip
      if (!event.trip_id) {
        setActiveTrip(null);
        return;
      }
      
      // Если есть trip_id - перезагружаем полные данные рейса
      // Это важно для получения правильного trip_type и других актуальных данных
      if (event.trip_id) {
        // Сразу отображаем рейс и его тип, не дожидаясь ответа API
        setActiveTrip((prev) => ({
          cycle_id: event.trip_id!,
          vehicle_id: prev?.vehicle_id ?? VEHICLE_ID,
          trip_type: event.trip_type || prev?.trip_type || 'planned',
          task_id: prev?.task_id ?? event.task_id ?? null,
          shift_id: prev?.shift_id ?? null,
          start_time: prev?.start_time ?? new Date().toISOString(),
          loading_point_id: prev?.loading_point_id ?? null,
          loading_tag: prev?.loading_tag ?? null,
          current_state: event.state || prev?.current_state || 'idle',
          last_tag: event.tag || prev?.last_tag || null,
          last_point_id: prev?.last_point_id ?? null,
        }));

        tripServiceApi
          .getActiveTrip()
          .then((trip) => {
            if (trip && trip.cycle_id) {
              setActiveTrip(trip);
            } else {
              // Рейса больше нет - очищаем
              setActiveTrip(null);
            }
          })
          .catch((err) => {
            console.error('Failed to reload active trip:', err);
            // Оставляем оптимистичное состояние, но обновляем только состояние и тег
            setActiveTrip((prev) =>
              prev
                ? {
                    ...prev,
                    current_state: event.state || prev.current_state,
                    last_tag: event.tag || prev.last_tag,
                  }
                : prev,
            );
          });
      }
    }
  }, []);
  
  // Обновление времени выполнения рейса в реальном времени (каждую секунду)
  useEffect(() => {
    if (!activeTrip || !activeTrip.start_time) {
      return;
    }
    
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    
    return () => clearInterval(interval);
  }, [activeTrip]);
  
  // Обработчик location событий из SSE
  const handleLocationEvent = useCallback((event: TagEvent) => {
    
    // Обновляем текущую локацию
    if (event.point_id) {
      setCurrentLocation(event.point_id);
    } else {
      setCurrentLocation(null);
    }
  }, []);

  const handleWeightEvent = useCallback((event: WeightEvent) => {
    if (!event || event.value === undefined || event.value === null) {
      return;
    }
    const numericValue = typeof event.value === 'string' ? Number(event.value) : event.value;
    if (!Number.isNaN(numericValue)) {
      setCurrentWeight(numericValue);
    }
  }, []);

  // Загрузить данные о текущем маршруте и рейсе (только при монтировании)
  const loadMainData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Получить текущее состояние State Machine (всегда есть)
      const stateMachineState = await tripServiceApi.getCurrentState();
      
      // Инициализируем currentState из State Machine
      setCurrentState(stateMachineState.state);
      
      // Инициализируем currentLocation из State Machine
      if (stateMachineState.last_point_id) {
        setCurrentLocation(stateMachineState.last_point_id);
      }
      
      // Получить активное задание
      const task = await tripServiceApi.getActiveTask();
      setActiveTask(task);

      // Получить активный рейс (если есть)
      try {
        const trip = await tripServiceApi.getActiveTrip();
        // Проверяем, что рейс действительно активен (есть cycle_id)
        if (trip && trip.cycle_id) {
          setActiveTrip(trip);
        } else {
          setActiveTrip(null);
        }
      } catch (tripErr) {
        // Нет активного рейса - это нормально
        setActiveTrip(null);
      }

      // Получить количество завершенных рейсов для текущего задания
      if (task && task.task_id) {
        try {
          const completedTrips = await tripServiceApi.getCompletedTripsCount(task.task_id);
          setCompletedTripsCount(completedTrips);
        } catch (tripCountErr) {
          console.error('Failed to load completed trips count:', tripCountErr);
          setCompletedTripsCount(0);
        }
      }
    } catch (err: any) {
      console.error('Failed to load main data:', err);
      if (err.response?.status === 404) {
        // Нет активного задания - это нормально
        setActiveTask(null);
        setActiveTrip(null);
        setCompletedTripsCount(0);
      } else {
        setError('Ошибка загрузки данных');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadPlaces = useCallback(async () => {
    try {
      const response = await graphServiceApi.getPlaces({ limit: 1000, offset: 0 });
      const map: Record<string, string> = {};
      response.items.forEach((place) => {
        // Индексируем по place.id (число)
        map[String(place.id)] = place.name;
        // Также индексируем по tag_point_id для совместимости
        if (place.tag_point_id) {
          map[place.tag_point_id] = place.name;
        }
      });
      setPlacesMap(map);
    } catch (placesError) {
      console.error('Failed to load places:', placesError);
    }
  }, []);

  // Инициализация: загрузить данные и подключиться к SSE
  useEffect(() => {
    console.log('🚀 MainPage mounted, initializing SSE...');
    
    // Загружаем данные при монтировании
    loadMainData();

    // Подключаемся к SSE для real-time обновлений состояний
    const stateEventSource = new EventSource(`${API_URL}/api/events/stream/${VEHICLE_ID}`);
    
    stateEventSource.onopen = () => {
      console.log('✅ SSE state connection established');
    };
    
    stateEventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as StateTransitionEvent;
        
        // Обрабатываем события state_transition и trip_completed
        if (data.event_type === 'state_transition' || data.event_type === 'trip_completed') {
          handleSSEEvent(data);
        }
      } catch (error) {
        console.error('Failed to parse SSE state message:', error);
      }
    };
    
    stateEventSource.onerror = (error) => {
      console.error('❌ SSE state connection error:', error);
      // EventSource автоматически переподключается
    };

    // Подключаемся к SSE для real-time обновлений локации
    const locationEventSource = new EventSource(`${API_URL}/api/events/stream/${VEHICLE_ID}/location`);
    
    locationEventSource.onopen = () => {
      console.log('✅ SSE location connection established');
    };
    
    locationEventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as TagEvent;
        
        // Обрабатываем только реальные события локации
        if (data.point_id !== undefined) {
          handleLocationEvent(data);
        }
      } catch (error) {
        console.error('Failed to parse SSE location message:', error);
      }
    };
    
    locationEventSource.onerror = (error) => {
      console.error('❌ SSE location connection error:', error);
      // EventSource автоматически переподключается
    };

    // Подключаемся к SSE для real-time обновлений веса
    const weightEventSource = new EventSource(`${API_URL}/api/events/stream/${VEHICLE_ID}/weight`);

    weightEventSource.onopen = () => {
      console.log('✅ SSE weight connection established');
    };

    weightEventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WeightEvent;
        if (data.value !== undefined) {
          handleWeightEvent(data);
        }
      } catch (sseError) {
        console.error('Failed to parse SSE weight message:', sseError);
      }
    };

    weightEventSource.onerror = (error) => {
      console.error('❌ SSE weight connection error:', error);
    };

    // Cleanup при размонтировании
    return () => {
      console.log('🛑 MainPage unmounting, closing SSE connections...');
      stateEventSource.close();
      locationEventSource.close();
      weightEventSource.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Пустой массив - выполняется только при монтировании!

  useEffect(() => {
    loadPlaces();
  }, [loadPlaces]);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const getPlaceLabel = useCallback(
    (placeId?: number | string | null) => {
      if (!placeId && placeId !== 0) {
        return '—';
      }
      const placeIdStr = String(placeId);
      return placesMap[placeIdStr] || placeIdStr;
    },
    [placesMap],
  );

  // Получить текст статуса рейса
  const getTripStatusText = (state: string): string => {
    const statusMap: Record<string, string> = {
      idle: 'Ожидание',
      moving_empty: 'Движение порожним',
      stopped_empty: 'Остановка порожним',
      loading: 'Погрузка',
      moving_loaded: 'Движение с грузом',
      stopped_loaded: 'Остановка с грузом',
      unloading: 'Разгрузка',
    };
    return statusMap[state] || state;
  };

  if (loading) {
    return <div className="main-page"><div className="loading">Загрузка...</div></div>;
  }

  if (!activeTask) {
    return (
      <div className="main-page">
        <div className="no-task">
          <h2>Нет активного задания</h2>
          <p>Перейдите в "Список заданий" чтобы начать смену</p>
        </div>
      </div>
    );
  }

  // Поддержка обоих полей: trips_count (новое) и trip_count (старое)
  const plannedTrips =
    activeTask.planned_trips_count ??
    activeTask.extra_data?.trips_count ??
    activeTask.extra_data?.trip_count ??
    0;

  const factTrips =
    completedTripsCount > 0
      ? completedTripsCount
      : activeTask.actual_trips_count ?? completedTripsCount;

  const progressPercent = plannedTrips > 0 ? Math.round((factTrips / plannedTrips) * 100) : 0;

  // Место назначения зависит от наличия активного рейса:
  // - Если рейс выполняется → место разгрузки (place_b_id)
  // - Если рейса нет → место погрузки (place_a_id)
  const currentDestination = activeTrip && activeTrip.cycle_id
    ? activeTask.place_b_id  // Рейс активен - показываем место разгрузки
    : activeTask.place_a_id; // Рейса нет - показываем место погрузки
  const destinationLabel = getPlaceLabel(currentDestination);
  const loadingPlaceLabel = getPlaceLabel(activeTask.place_a_id);
  const unloadingPlaceLabel = getPlaceLabel(activeTask.place_b_id);
  const currentLocationLabel = getPlaceLabel(currentLocation);
  
  // Показываем тип рейса только если рейс активен (есть cycle_id)
  const tripTypeLabel = activeTrip && activeTrip.cycle_id
    ? activeTrip.trip_type === 'planned'
      ? 'Плановый рейс'
      : 'Внеплановый рейс'
    : 'Движение к рейсу';
  
  // Вычисляем время выполнения рейса в секундах
  const getTripDurationSeconds = (): number | null => {
    if (!activeTrip || !activeTrip.start_time) {
      return null;
    }
    
    const startTime = new Date(activeTrip.start_time).getTime();
    const endTime = activeTrip.end_time 
      ? new Date(activeTrip.end_time).getTime()
      : currentTime.getTime();
    
    const durationMs = endTime - startTime;
    return Math.floor(durationMs / 1000);
  };
  
  const tripDurationSeconds = getTripDurationSeconds();
  const formatTripDuration = (seconds: number | null): string => {
    if (seconds === null) {
      return '—';
    }
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}ч ${minutes}м ${secs}с`;
    } else if (minutes > 0) {
      return `${minutes}м ${secs}с`;
    } else {
      return `${secs}с`;
    }
  };

  return (
    <div className="main-page">
      <main className="main-display">
        <header className="destination-header">
          <div className="destination-info">
            <p className="destination-label">Место назначения:</p>
            <h1 className="destination-title">{destinationLabel}</h1>
            <p className="current-point">
              Текущая точка: {currentLocationLabel}
            </p>
          </div>
          <div className="driver-info">
            <div className="driver-name">Иван Иванович</div>
            <div className="driver-meta">
              <span>#001</span>
              <span>{currentTime.toLocaleDateString('ru-RU', {
                day: '2-digit', month: '2-digit', year: 'numeric',
              })}</span>
              <span>{currentTime.toLocaleTimeString('ru-RU', {
                hour: '2-digit', minute: '2-digit',
              })}</span>
            </div>
            <div className="driver-stats">
              <div>
                <span>Время выполнения рейса:</span>
                <strong>{formatTripDuration(tripDurationSeconds)}</strong>
              </div>
              <div>
                <span>Текущий вес:</span>
                <strong>{currentWeight !== null ? currentWeight.toFixed(1) : '—'}</strong>
              </div>
            </div>
          </div>
        </header>

        <section className="status-panel">
          <div className="status-card state-card">
            <div className="state-title">
              {tripTypeLabel}
            </div>
            <div className="state-value">{getTripStatusText(currentState)}</div>
          </div>

          <div className="status-card progress-card">
            <div className="progress-title">Количество рейсов за смену</div>
            <div className="progress-values">
              <span className="fact">Факт {factTrips}</span>
              <span className="plan">/ План {plannedTrips}</span>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progressPercent}%` }}>
                {progressPercent > 10 && <span>{progressPercent}%</span>}
              </div>
            </div>
          </div>

          <div className="status-card route-card">
            <div>
              <div className="route-label">Место погрузки:</div>
              <div className="route-value">{loadingPlaceLabel}</div>
            </div>
            <div>
              <div className="route-label">Место разгрузки:</div>
              <div className="route-value">{unloadingPlaceLabel}</div>
            </div>
          </div>
        </section>
      </main>

      {error && <div className="error-message">{error}</div>}
    </div>
  );
};
