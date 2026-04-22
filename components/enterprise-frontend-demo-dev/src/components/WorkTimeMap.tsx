import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { MouseEvent as ReactMouseEvent } from 'react';
import { Loader2, Plus, Edit, Trash2, X } from 'lucide-react';
import { eventLogApi, vehiclesApi, workRegimesApi, cycleHistoryApi } from '../api/client';
import type { CycleStateHistoryItem, Vehicle, VehicleState, ShiftDefinition } from '../types';

type LiveEventsMap = Record<string, CycleStateHistoryItem[]>;

type ModalMode = 'create' | 'edit' | 'delete';

interface IntervalModalData {
  mode: ModalMode;
  segment?: TimelineSegment;
  vehicleId: number;
  isLiveState?: boolean; // Флаг для live state (последнего актуального интервала)
}

interface TimelineSegment {
  startPercent: number;
  endPercent: number;
  state: VehicleState;
  startTime: Date;
  endTime: Date;
  recordId?: string; // ID записи в БД для редактирования
}

interface VehicleTimelineData {
  vehicle: Vehicle;
  segments: TimelineSegment[];
  hasData: boolean;
  liveState?: {
    state: VehicleState;
    startTime: Date;
    recordId?: string;
  };
}

const STATE_META: Record<
  VehicleState,
  {
    label: string;
    color: string;
  }
> = {
  idle: { label: 'Ожидание погрузки', color: '#FFFC29' },
  loading: { label: 'Погрузка', color: '#EB74B2' },
  moving_loaded: { label: 'Движение гружёным', color: '#87F915' },
  stopped_loaded: { label: 'Остановка гружёным', color: '#7EE006' },
  unloading: { label: 'Разгрузка', color: '#E6E7E4' },
  moving_empty: { label: 'Движение порожним', color: '#BECAE0' },
  stopped_empty: { label: 'Остановка порожним', color: '#9EB0D1' },
};

const NEUTRAL_COLOR = '#1f2937';
const HOUR_MS = 60 * 60 * 1000;
const TEN_MIN_MS = 10 * 60 * 1000;
const MIN_DURATION_MS = TEN_MIN_MS;
const MAX_LIVE_EVENTS = 200;

function getDefaultDate() {
  return new Date().toISOString().split('T')[0];
}

function getShiftTimeRange(shift: ShiftDefinition) {
  // Используем либо offset_minutes (минуты), либо time_offset (секунды)
  const startOffset = shift.begin_offset_minutes ??
                     (shift.start_time_offset ? shift.start_time_offset / 60 : 0);
  const endOffset = shift.end_offset_minutes ??
                   (shift.end_time_offset ? shift.end_time_offset / 60 : 0);
  return { startOffset, endOffset };
}

function getDefaultShiftNum(shifts: ShiftDefinition[]): number {
  if (!shifts || shifts.length === 0) return 1;

  const now = new Date();
  const nowMinutes = now.getHours() * 60 + now.getMinutes();

  // Найти смену, которая активна сейчас
  for (const shift of shifts) {
    const { startOffset, endOffset } = getShiftTimeRange(shift);

    if (startOffset < endOffset) {
      // Смена в пределах одного дня
      if (nowMinutes >= startOffset && nowMinutes < endOffset) {
        return shift.shift_num;
      }
    } else {
      // Смена пересекает полночь
      if (nowMinutes >= startOffset || nowMinutes < endOffset) {
        return shift.shift_num;
      }
    }
  }

  // Если ни одна смена не активна, возвращаем первую
  return shifts[0].shift_num;
}

function getShiftBounds(date: string, shift: ShiftDefinition) {
  const base = new Date(`${date}T00:00:00`);
  const { startOffset, endOffset } = getShiftTimeRange(shift);

  // Вычисляем время начала
  const start = new Date(base);
  start.setHours(Math.floor(startOffset / 60), startOffset % 60, 0, 0);

  // Вычисляем время конца
  const end = new Date(base);
  if (endOffset >= startOffset) {
    // Смена в пределах одного дня
    end.setHours(Math.floor(endOffset / 60), endOffset % 60, 0, 0);
  } else {
    // Смена пересекает полночь
    end.setDate(end.getDate() + 1);
    end.setHours(Math.floor(endOffset / 60), endOffset % 60, 0, 0);
  }

  return { start, end };
}

function calculateShiftTime(shift: ShiftDefinition): string {
  // Используем либо offset_minutes (минуты), либо time_offset (секунды)
  const offsetMinutes = shift.begin_offset_minutes ??
                       (shift.start_time_offset ? shift.start_time_offset / 60 : 0);
  const hours = Math.floor(offsetMinutes / 60);
  const minutes = offsetMinutes % 60;
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
}

function formatShiftLabel(shift: ShiftDefinition): string {
  const startTime = calculateShiftTime(shift);
  const { endOffset } = getShiftTimeRange(shift);
  const endHours = Math.floor(endOffset / 60);
  const endMinutes = endOffset % 60;
  const endTime = `${endHours.toString().padStart(2, '0')}:${endMinutes.toString().padStart(2, '0')}`;
  return `${shift.name || `Смена ${shift.shift_num}`}: ${startTime} — ${endTime}`;
}

const isKnownState = (state: string): state is VehicleState => state in STATE_META;

function formatTimeLabel(date: Date) {
  return date.toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function WorkTimeMap() {
  const queryClient = useQueryClient();
  const [selectedDate, setSelectedDate] = useState(getDefaultDate());
  const [selectedShiftNum, setSelectedShiftNum] = useState<number>(1);
  const [intervalModal, setIntervalModal] = useState<IntervalModalData | null>(null);

  const workRegimeQuery = useQuery({
    queryKey: ['work-regime', 1],
    queryFn: () => workRegimesApi.getActive(),
    staleTime: 300_000, // 5 минут
  });

  // Устанавливаем дефолтную смену при загрузке work_regime
  useEffect(() => {
    if (workRegimeQuery.data?.shifts_definition) {
      const defaultShiftNum = getDefaultShiftNum(workRegimeQuery.data.shifts_definition);
      setSelectedShiftNum(defaultShiftNum);
    }
  }, [workRegimeQuery.data]);

  // Получаем выбранную смену из work_regime
  const selectedShift = workRegimeQuery.data?.shifts_definition?.find(
    shift => shift.shift_num === selectedShiftNum
  );

  // Используем первую смену как дефолтную, если текущая не найдена
  const shiftOption = selectedShift || workRegimeQuery.data?.shifts_definition?.[0];
  const { start: shiftStart, end: shiftEnd } = useMemo(
    () => shiftOption ? getShiftBounds(selectedDate, shiftOption) : { start: new Date(), end: new Date() },
    [selectedDate, shiftOption],
  );
  const shiftStartMs = shiftStart.getTime();
  const shiftEndMs = shiftEnd.getTime();
  const shiftDurationMs = shiftEndMs - shiftStartMs;

  const [viewStartMs, setViewStartMs] = useState(shiftStartMs);
  const [viewDurationMs, setViewDurationMs] = useState(shiftDurationMs);
  const viewEndMs = viewStartMs + viewDurationMs;
  const [isFollowing, setIsFollowing] = useState(false);
  const isFollowingRef = useRef(isFollowing);
  const prevShiftBoundsRef = useRef({ shiftStartMs, shiftEndMs });

  // Синхронизируем ref с состоянием
  useEffect(() => {
    isFollowingRef.current = isFollowing;
  }, [isFollowing]);

  useEffect(() => {
    const prevBounds = prevShiftBoundsRef.current;
    const shiftChanged = prevBounds.shiftStartMs !== shiftStartMs || prevBounds.shiftEndMs !== shiftEndMs;
    
    if (shiftChanged && isFollowingRef.current) {
      // При изменении смены/даты отключаем режим слежения
      setIsFollowing(false);
    }
    
    // Обновляем view только если не в режиме слежения
    if (!isFollowingRef.current) {
      setViewDurationMs(shiftDurationMs);
      setViewStartMs(shiftStartMs);
    }
    
    prevShiftBoundsRef.current = { shiftStartMs, shiftEndMs };
  }, [shiftDurationMs, shiftStartMs, shiftEndMs]);

  const [currentTimeMs, setCurrentTimeMs] = useState(Date.now());
  useEffect(() => {
    const interval = window.setInterval(() => setCurrentTimeMs(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  // Автоматическое слежение за текущим временем
  useEffect(() => {
    if (!isFollowing) {
      return;
    }
    // Устанавливаем зум на 1 час
    setViewDurationMs(HOUR_MS);
    // Текущее время должно быть на 10 минут от правого края
    // viewEndMs = currentTimeMs + TEN_MIN_MS
    // viewStartMs = viewEndMs - viewDurationMs = currentTimeMs + TEN_MIN_MS - HOUR_MS
    const newViewStart = currentTimeMs + TEN_MIN_MS - HOUR_MS;
    // Ограничиваем границами смены
    const minStart = shiftStartMs;
    const maxStart = shiftEndMs - HOUR_MS;
    const clampedStart = Math.max(minStart, Math.min(maxStart, newViewStart));
    setViewStartMs(clampedStart);
  }, [currentTimeMs, isFollowing, shiftStartMs, shiftEndMs]);

  const isCurrentShift = currentTimeMs >= shiftStartMs && currentTimeMs <= shiftEndMs;

  const vehiclesQuery = useQuery({
    queryKey: ['vehicles', 'work-time-map'],
    queryFn: () =>
      vehiclesApi.list({
        enterprise_id: 1,
        is_active: true,
        size: 100,
      }),
  });

  const stateHistoryQuery = useQuery({
    queryKey: ['state-history', selectedDate, selectedShiftNum],
    queryFn: () =>
      eventLogApi.getStateHistory({
        from_date: selectedDate,
        to_date: selectedDate,
        from_shift_num: selectedShiftNum,
        to_shift_num: selectedShiftNum,
        // Без size - получаем все записи за смену без пагинации
      }),
    staleTime: 60_000,
  });

  // Мутации для работы с интервалами
  const batchUpsertMutation = useMutation({
    mutationFn: (data: any) =>
      cycleHistoryApi.batchUpsert(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['state-history'] });
      setIntervalModal(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: ({ recordId, data }: { recordId: string; data: any }) => {
      console.log('Starting delete mutation', { recordId, data });
      return cycleHistoryApi.delete(recordId, data);
    },
    onSuccess: (result) => {
      console.log('Delete mutation success', result);
      queryClient.invalidateQueries({ queryKey: ['state-history'] });
      setIntervalModal(null);
    },
    onError: (error) => {
      console.error('Delete mutation error', error);
    },
  });

  const [liveEvents, setLiveEvents] = useState<LiveEventsMap>({});
  const sseConnectionRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => {
      if (sseConnectionRef.current) {
        sseConnectionRef.current.close();
        sseConnectionRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    // Закрываем предыдущее соединение если есть
    if (sseConnectionRef.current) {
      sseConnectionRef.current.close();
    }

    // Создаем единое соединение для всех событий
    // SSE может не работать через Vite proxy, пробуем прямое подключение
    const source = new EventSource('/api/events/stream/all');
    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        console.log('SSE received event:', payload);

        if (payload?.event_type === 'state_transition') {
          // Обработка переходов состояний
          const vehicleId = payload.vehicle_id;
          if (!vehicleId) {
            console.warn('Received state_transition event without vehicle_id', payload);
            return;
          }

          // Новый формат уже содержит timestamp в ISO формате и все нужные поля
          const state: VehicleState = isKnownState(payload.state)
            ? payload.state
            : 'idle';

          const item: CycleStateHistoryItem = {
            id: payload.id,
            timestamp: payload.timestamp,
            vehicle_id: vehicleId,
            cycle_id: payload.cycle_id || null,
            state,
            source: payload.source,
            task_id: payload.task_id || null,
            place_id: payload.place_id || null,
          };

          setLiveEvents((prev) => {
            const existing = prev[vehicleId] ?? [];
            const updated = [...existing, item].slice(-MAX_LIVE_EVENTS);
            return { ...prev, [vehicleId]: updated };
          });
        } else if (payload?.event_type === 'history_changed') {
          // Обработка изменений истории статусов
          const vehicleId = payload.vehicle_id;
          if (!vehicleId) {
            console.warn('Received history_changed event without vehicle_id', payload);
            return;
          }

          console.log('🔄 Processing history_changed event, refreshing data for vehicle', vehicleId, payload);

          // Инвалидируем кэш для данных истории состояний
          queryClient.invalidateQueries({
            queryKey: ['event-log', 'state-history'],
            exact: false
          });
        } else {
          console.log('Ignoring unknown event type:', payload?.event_type, payload);
        }
      } catch (error) {
        console.error('Failed to parse SSE event', error);
      }
    };

    source.onerror = (error) => {
      console.error('SSE connection error for all events', error);
    };

    sseConnectionRef.current = source;

    // Очищаем соединение при изменении зависимостей
    return () => {
      if (source) {
        source.close();
      }
    };
  }, []); // Пустой массив зависимостей - соединение создается один раз

  const groupedHistory = useMemo(() => {
    const map = new Map<string, CycleStateHistoryItem[]>();
    if (stateHistoryQuery.data?.items) {
      stateHistoryQuery.data.items.forEach((item) => {
        const vehicleKey = String(item.vehicle_id);
        const existing = map.get(vehicleKey) ?? [];
        existing.push(item);
        map.set(vehicleKey, existing);
      });
    }

    Object.entries(liveEvents).forEach(([vehicleId, events]) => {
      if (!events.length) {
        return;
      }
      const existing = map.get(vehicleId) ?? [];
      map.set(vehicleId, [...existing, ...events]);
    });

    map.forEach((items, key) => {
      map.set(
        key,
        [...items].sort(
          (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
        ),
      );
    });

    return map;
  }, [liveEvents, stateHistoryQuery.data]);

  const buildTimeline = useCallback(
    (vehicle: Vehicle): VehicleTimelineData => {
      const vehicleKey = vehicle.id ? String(vehicle.id) : null;
      if (!vehicleKey) {
        return { vehicle, segments: [], hasData: false };
      }

      const events = groupedHistory.get(vehicleKey) ?? [];
      const sortedEvents = [...events].sort(
        (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      );
      if (sortedEvents.length === 0) {
        return { vehicle, segments: [], hasData: false };
      }

      const startMs = viewStartMs;
      const endMs = viewEndMs;
      const duration = Math.max(viewDurationMs, 1);
      const nowLimit = isCurrentShift ? Math.min(endMs, currentTimeMs) : endMs;
      const hasVisibleRange = nowLimit > startMs;
      let liveState;

      const segments: TimelineSegment[] = [];
      let previousState: VehicleState = 'idle'; // Начинаем с idle состояния
      let lastTime = startMs;
      let hasStarted = false; // Флаг, что начали показывать события

      const clampTime = (value: number) => {
        const clamped = Math.min(Math.max(value, startMs), nowLimit);
        return clamped;
      };

      const pushSegment = (segmentStart: number, segmentEnd: number, state: VehicleState, recordId?: string) => {
        if (segmentEnd <= segmentStart) {
          return;
        }
        segments.push({
          startPercent: ((segmentStart - startMs) / duration) * 100,
          endPercent: ((segmentEnd - startMs) / duration) * 100,
          state,
          startTime: new Date(segmentStart),
          endTime: new Date(segmentEnd),
          recordId,
        });
      };

      sortedEvents.forEach((event, index) => {
        const normalizedState = isKnownState(event.state) ? event.state : 'idle';
        const eventTime = clampTime(new Date(event.timestamp).getTime());

        // Начинаем показывать только после первого события
        if (!hasStarted) {
          hasStarted = true;
          lastTime = eventTime; // Начинаем с времени первого события
          previousState = normalizedState;
          if (index === events.length - 1) {
            liveState = {
              state: normalizedState,
              startTime: new Date(eventTime),
              recordId: event.id // ID записи для live состояния
            };
          }
          return;
        }

        if (hasVisibleRange) {
          // Передаем ID предыдущего события для сегмента
          const segmentStartEvent = sortedEvents[index - 1];
          pushSegment(lastTime, eventTime, previousState, segmentStartEvent?.id);
        }

        lastTime = Math.max(eventTime, lastTime);
        previousState = normalizedState;
        if (index === events.length - 1) {
          liveState = {
            state: normalizedState,
            startTime: new Date(eventTime),
            recordId: event.id // ID записи для live состояния
          };
        }
      });

      // Добавляем финальный сегмент только если были события
      if (hasStarted && hasVisibleRange) {
        // Используем ID последнего события для финального сегмента
        const lastEvent = sortedEvents[sortedEvents.length - 1];
        pushSegment(lastTime, nowLimit, previousState, lastEvent?.id);
      }

      return { vehicle, segments, hasData: segments.length > 0, liveState };
    },
    [currentTimeMs, groupedHistory, isCurrentShift, viewDurationMs, viewEndMs, viewStartMs],
  );

  const timelines = useMemo(() => {
    if (!vehiclesQuery.data?.items) {
      return [];
    }
    return vehiclesQuery.data.items.map((vehicle) => buildTimeline(vehicle));
  }, [buildTimeline, vehiclesQuery.data]);

  const hourLabels = useMemo(() => {
    const labels: string[] = [];
    const stepMs = viewDurationMs <= HOUR_MS ? TEN_MIN_MS : HOUR_MS;
    let current = viewStartMs;
    while (current <= viewEndMs + 1000) {
      labels.push(formatTimeLabel(new Date(current)));
      current += stepMs;
    }
    return labels.length > 0 ? labels : [formatTimeLabel(new Date(viewStartMs))];
  }, [viewDurationMs, viewEndMs, viewStartMs]);

  const isLoading = workRegimeQuery.isLoading || vehiclesQuery.isLoading || stateHistoryQuery.isLoading;

  const timelineRef = useRef<HTMLDivElement>(null);
  const dragStateRef = useRef<{ startX: number; viewStart: number } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const tooltipTimerRef = useRef<number | null>(null);
  const [tooltip, setTooltip] = useState<{ segment: TimelineSegment; x: number; y: number } | null>(
    null,
  );


  const clearTooltipTimer = useCallback(() => {
    if (tooltipTimerRef.current) {
      window.clearTimeout(tooltipTimerRef.current);
      tooltipTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      clearTooltipTimer();
    };
  }, [clearTooltipTimer]);

  useEffect(() => {
    clearTooltipTimer();
    setTooltip(null);
  }, [clearTooltipTimer, viewDurationMs, viewStartMs]);

  const handleWheel = useCallback(
    (event: React.WheelEvent<HTMLDivElement>) => {
      if (isFollowing) {
        return;
      }
      if (!timelineRef.current) {
        return;
      }

      const rect = timelineRef.current.getBoundingClientRect();
      const ratioRaw = rect.width ? (event.clientX - rect.left) / rect.width : 0.5;
      const ratio = Math.min(1, Math.max(0, ratioRaw));

      const zoomOut = event.deltaY > 0;
      const factor = zoomOut ? 1.1 : 0.9;
      const maxDuration = shiftDurationMs;
      let nextDuration = viewDurationMs * factor;
      nextDuration = Math.min(maxDuration, Math.max(MIN_DURATION_MS, nextDuration));
      if (nextDuration === viewDurationMs) {
        return;
      }

      const center = viewStartMs + viewDurationMs * ratio;
      let nextStart = center - nextDuration * ratio;
      const minStart = shiftStartMs;
      const maxStart = shiftEndMs - nextDuration;
      if (nextStart < minStart) {
        nextStart = minStart;
      } else if (nextStart > maxStart) {
        nextStart = maxStart;
      }

      setViewDurationMs(nextDuration);
      setViewStartMs(nextStart);
    },
    [isFollowing, shiftDurationMs, shiftEndMs, shiftStartMs, viewDurationMs, viewStartMs],
  );

 // Включаем зависимости обратно

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (isFollowing || viewDurationMs >= shiftDurationMs || !timelineRef.current) {
        return;
      }
      setIsDragging(true);
      dragStateRef.current = {
        startX: event.clientX,
        viewStart: viewStartMs,
      };
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [isFollowing, shiftDurationMs, viewDurationMs, viewStartMs],
  );

  const handlePointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!isDragging || !timelineRef.current || !dragStateRef.current) {
        return;
      }
      const rect = timelineRef.current.getBoundingClientRect();
      if (!rect.width) {
        return;
      }
      const deltaPx = event.clientX - dragStateRef.current.startX;
      const deltaTime = (deltaPx / rect.width) * viewDurationMs;
      let nextStart = dragStateRef.current.viewStart - deltaTime;
      const minStart = shiftStartMs;
      const maxStart = shiftEndMs - viewDurationMs;
      if (nextStart < minStart) {
        nextStart = minStart;
      } else if (nextStart > maxStart) {
        nextStart = maxStart;
      }
      setViewStartMs(nextStart);
    },
    [isDragging, shiftEndMs, shiftStartMs, viewDurationMs],
  );

  const stopDragging = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (isDragging) {
        setIsDragging(false);
        dragStateRef.current = null;
        if (event.currentTarget.hasPointerCapture(event.pointerId)) {
          event.currentTarget.releasePointerCapture(event.pointerId);
        }
      }
    },
    [isDragging],
  );

  const handleSegmentHoverStart = useCallback(
    (segment: TimelineSegment, event: ReactMouseEvent<HTMLDivElement>) => {
      clearTooltipTimer();
      const { clientX, clientY } = event;
      tooltipTimerRef.current = window.setTimeout(() => {
        setTooltip({ segment, x: clientX + 12, y: clientY + 12 });
      }, 500);
    },
    [clearTooltipTimer],
  );

  const handleSegmentClick = useCallback(
    (segment: TimelineSegment, vehicleId: number) => {
      console.log('handleSegmentClick called', { segment, vehicleId, recordId: segment.recordId });

      // Определяем, является ли сегмент live state (последним актуальным интервалом)
      const isLiveState = !segment.recordId;

      setIntervalModal({
        mode: 'edit',
        segment,
        vehicleId,
        isLiveState, // Добавляем флаг для live state
      });
    },
    [],
  );

  const handleSegmentHoverEnd = useCallback(() => {
    clearTooltipTimer();
    setTooltip(null);
  }, [clearTooltipTimer]);

  const canPan = viewDurationMs < shiftDurationMs - 1;
  const showCurrentIndicator = isCurrentShift && currentTimeMs >= viewStartMs && currentTimeMs <= viewEndMs;
  const currentIndicatorPercent = showCurrentIndicator
    ? ((currentTimeMs - viewStartMs) / viewDurationMs) * 100
    : null;

  return (
    <>
      <div className="min-h-screen bg-dark-bg py-8 text-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mt-4 rounded-xl border border-dark-border bg-dark-card p-4 shadow-lg shadow-black/30">
            <div className="flex flex-wrap items-center justify-between gap-4 text-sm text-gray-200">
              <div className="flex flex-wrap items-center gap-4">
                <label className="flex items-center gap-2">
                  <span>Дата</span>
                  <input
                    type="date"
                    value={selectedDate}
                    onChange={(event) => setSelectedDate(event.target.value)}
                    className="rounded-lg border border-dark-border bg-dark-bg px-3 py-2 text-white ring-primary-orange/30 focus:border-primary-orange focus:outline-none focus:ring-2"
                  />
                </label>
                <label className="flex items-center gap-2">
                  <span>Смена</span>
                  <select
                    value={selectedShiftNum}
                    onChange={(event) => setSelectedShiftNum(Number(event.target.value))}
                    className="rounded-lg border border-dark-border bg-dark-bg px-3 py-2 text-white ring-primary-orange/30 focus:border-primary-orange focus:outline-none focus:ring-2"
                  >
                    {workRegimeQuery.data?.shifts_definition?.map((shift) => (
                      <option key={shift.shift_num} value={shift.shift_num}>
                        {formatShiftLabel(shift)}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setIsFollowing(!isFollowing)}
                  className="rounded-lg border border-primary-orange bg-primary-orange px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-orange/90 focus:outline-none focus:ring-2 focus:ring-primary-orange/50"
                >
                  {isFollowing ? 'Прекратить следить' : 'Следить'}
                </button>
                <button
                  onClick={() => {
                    // Для создания нового интервала используем первый vehicle из списка
                    const firstVehicle = vehiclesQuery.data?.items?.[0];
                    if (firstVehicle) {
                      setIntervalModal({
                        mode: 'create',
                        vehicleId: firstVehicle.id,
                      });
                    }
                  }}
                  className="rounded-lg border border-green-600 bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-600/90 focus:outline-none focus:ring-2 focus:ring-green-600/50"
                >
                  <Plus className="inline h-4 w-4" />
                </button>
              </div>
            </div>
          </div>

          <div className="mt-6 rounded-2xl border border-dark-border bg-dark-card shadow-lg shadow-black/30">
            <div className="border-b border-dark-border px-6 py-4">
              <div className="flex flex-wrap items-center gap-4 text-sm text-gray-300">
                {Object.entries(STATE_META).map(([state, meta]) => (
                  <div key={state} className="flex items-center gap-2">
                    <span className="h-3 w-3 rounded border border-dark-border" style={{ backgroundColor: meta.color }} />
                    {meta.label}
                  </div>
                ))}
              </div>
            </div>

            {isLoading ? (
              <div className="flex items-center justify-center gap-3 py-12 text-gray-300">
                <Loader2 className="h-5 w-5 animate-spin" />
                Загрузка данных...
              </div>
            ) : vehiclesQuery.isError || stateHistoryQuery.isError ? (
              <div className="py-12 text-center text-sm text-red-400">
                Не удалось загрузить данные. Попробуйте обновить страницу.
              </div>
            ) : (
              <div
                ref={timelineRef}
                className={`select-none ${
                  canPan ? 'cursor-grab active:cursor-grabbing' : 'cursor-default'
                }`}
                style={{
                  overscrollBehavior: 'contain',
                  touchAction: 'none'
                }}
                onWheel={handleWheel}
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onPointerUp={stopDragging}
                onPointerLeave={stopDragging}
                onPointerCancel={stopDragging}
              >
                {timelines.map((timeline) => (
                  <TimelineRow
                    key={timeline.vehicle.id}
                    timeline={timeline}
                    onSegmentHoverStart={handleSegmentHoverStart}
                    onSegmentHoverEnd={handleSegmentHoverEnd}
                    onSegmentClick={handleSegmentClick}
                    currentIndicatorPercent={currentIndicatorPercent}
                    viewStartMs={viewStartMs}
                    viewDurationMs={viewDurationMs}
                  />
                ))}
              </div>
            )}
          </div>

          <div className="mt-8 border-t border-dashed border-gray-700 pt-4">
            <div className="flex justify-between text-xs text-gray-400">
              {hourLabels.map((label, index) => (
                <span key={`${label}-${index}`}>{label}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
      {tooltip && (
        <div
          className="pointer-events-none fixed z-50 rounded-lg bg-gray-900/90 px-3 py-2 text-xs text-white shadow-lg"
          style={{ top: tooltip.y, left: tooltip.x }}
        >
          <p className="font-semibold">{STATE_META[tooltip.segment.state].label}</p>
          <p>
            {tooltip.segment.startTime.toLocaleTimeString('ru-RU', {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })}{' '}
            —{' '}
            {tooltip.segment.endTime.toLocaleTimeString('ru-RU', {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })}
          </p>
        </div>
      )}

      {intervalModal && (
        <IntervalModal
          modalData={intervalModal}
          onClose={() => setIntervalModal(null)}
          onSwitchMode={setIntervalModal}
          onSave={async (data) => {
            await batchUpsertMutation.mutateAsync({
              vehicle_id: intervalModal.vehicleId,
              items: data.items,
            });
          }}
          onDelete={async (recordId, confirmData) => {
            await deleteMutation.mutateAsync({
              recordId,
              data: confirmData,
            });
          }}
          isLoading={batchUpsertMutation.isPending || deleteMutation.isPending}
        />
      )}
    </>
  );
}

function TimelineRow({
  timeline,
  onSegmentHoverStart,
  onSegmentHoverEnd,
  onSegmentClick,
  currentIndicatorPercent,
  viewStartMs,
  viewDurationMs,
}: {
  timeline: VehicleTimelineData;
  onSegmentHoverStart: (segment: TimelineSegment, event: ReactMouseEvent<HTMLDivElement>) => void;
  onSegmentHoverEnd: () => void;
  onSegmentClick: (segment: TimelineSegment, vehicleId: number) => void;
  currentIndicatorPercent: number | null;
  viewStartMs: number;
  viewDurationMs: number;
}) {
  const { vehicle, segments, hasData, liveState } = timeline;

  return (
    <div className="flex flex-col border-b border-dark-border px-6 py-5 last:border-b-0">
      <div className="flex flex-wrap items-center gap-4">
        <div className="w-40">
          <p className="font-semibold text-white">{vehicle.name}</p>
          <p className="text-xs uppercase text-gray-400">{vehicle.vehicle_type}</p>
        </div>
        <div className="flex-1">
          <div className="relative h-8 bg-dark-bg">
            {segments.length === 0 && (
              <div className="absolute inset-0" style={{ backgroundColor: NEUTRAL_COLOR }} />
            )}
            {segments.map((segment, index) => (
              <div
                key={`${vehicle.id}-segment-${index}`}
                className="absolute top-0 bottom-0 cursor-pointer"
                style={{
                  left: `${segment.startPercent}%`,
                  width: `${segment.endPercent - segment.startPercent}%`,
                  backgroundColor: STATE_META[segment.state].color,
                }}
                onMouseEnter={(event) => onSegmentHoverStart(segment, event)}
                onMouseLeave={onSegmentHoverEnd}
                onClick={() => onSegmentClick(segment, vehicle.id)}
              />
            ))}
            {liveState && currentIndicatorPercent !== null && (
              (() => {
                const rawStartPercent =
                  ((liveState.startTime.getTime() - viewStartMs) / viewDurationMs) * 100;
                const clampedStart = Math.min(100, Math.max(0, rawStartPercent));
                const width = Math.max(0, currentIndicatorPercent - clampedStart);
                if (width <= 0) {
                  return null;
                }
                const overlayStartTime = new Date(
                  Math.max(liveState.startTime.getTime(), viewStartMs),
                );
                const overlayEndTime = new Date(
                  viewStartMs + (currentIndicatorPercent / 100) * viewDurationMs,
                );
                return (
                  <div
                    className="absolute top-0 bottom-0 cursor-pointer"
                    style={{
                      left: `${clampedStart}%`,
                      width: `${width}%`,
                      backgroundColor: STATE_META[liveState.state].color,
                    }}
                    onMouseEnter={(event) =>
                      onSegmentHoverStart(
                        {
                          startPercent: clampedStart,
                          endPercent: clampedStart + width,
                          state: liveState.state,
                          startTime: overlayStartTime,
                          endTime: overlayEndTime,
                        },
                        event,
                      )
                    }
                    onMouseLeave={onSegmentHoverEnd}
                    onClick={() =>
                      onSegmentClick(
                        {
                          startPercent: clampedStart,
                          endPercent: clampedStart + width,
                          state: liveState.state,
                          startTime: overlayStartTime,
                          endTime: overlayEndTime,
                          recordId: liveState.recordId,
                        },
                        vehicle.id,
                      )
                    }
                  />
                );
              })()
            )}
            {currentIndicatorPercent !== null && (
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-red-500"
                style={{ left: `${currentIndicatorPercent}%` }}
              >
                <div className="absolute -top-1 h-2 w-2 -translate-x-1/2 rounded-full bg-red-500" />
              </div>
            )}
          </div>
          {!hasData && (
            <p className="mt-1 text-xs text-gray-500">Нет событий за выбранный период</p>
          )}
        </div>
      </div>
    </div>
  );
}

// Модальное окно для работы с интервалами
function IntervalModal({
  modalData,
  onClose,
  onSwitchMode,
  onSave,
  onDelete,
  isLoading,
}: {
  modalData: IntervalModalData;
  onClose: () => void;
  onSwitchMode: (modalData: IntervalModalData) => void;
  onSave: (data: any) => Promise<void>;
  onDelete: (recordId: string, confirmData: any) => Promise<void>;
  isLoading: boolean;
}) {
  // Конвертируем время из UTC в локальное для отображения в форме
  const getLocalTimeString = (utcDate?: Date) => {
    if (!utcDate) {
      // Для создания нового интервала используем текущее время в локальном формате
      const now = new Date();
      return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    }
    // Конвертируем UTC в локальное время для отображения
    const localDate = new Date(utcDate.getTime() - utcDate.getTimezoneOffset() * 60000);
    return localDate.toISOString().slice(0, 16);
  };

  const [formData, setFormData] = useState({
    timestamp: getLocalTimeString(modalData.segment?.startTime),
    system_name: modalData.segment?.state || 'idle',
    system_status: true,
  });

  // Получаем recordId из сегмента
  const recordId = modalData.segment?.recordId;
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deleteInfo, setDeleteInfo] = useState<{
    requiresConfirmation: boolean;
    confirmationMessage: string;
    cycleId: string;
  } | null>(null);
  const [isLoadingDeleteInfo, setIsLoadingDeleteInfo] = useState(false);

  // Сбрасываем состояния при изменении сегмента или режима
  useEffect(() => {
    setDeleteConfirm(false);
    setDeleteInfo(null);
    setIsLoadingDeleteInfo(false);
  }, [modalData.segment?.recordId, modalData.mode, setDeleteConfirm]);

  // Предварительный запрос при переходе в режим delete
  useEffect(() => {
    if (modalData.mode === 'delete' && recordId && modalData.vehicleId) {
      console.log('Making preliminary delete request for confirmation');
      setIsLoadingDeleteInfo(true);
      setDeleteInfo(null);

      cycleHistoryApi.delete(recordId, { confirm: false })
        .then(response => {
          console.log('Preliminary delete response', response);
          setDeleteInfo({
            requiresConfirmation: true, // Теперь всегда требуется подтверждение
            confirmationMessage: response.message || 'Вы уверены, что хотите удалить этот интервал?',
            cycleId: response.cycle_id || '',
          });
        })
        .catch(error => {
          console.error('Preliminary delete request failed', error);
          // В случае ошибки показываем обычное сообщение
          setDeleteInfo({
            requiresConfirmation: false,
            confirmationMessage: 'Вы уверены, что хотите удалить этот интервал?',
            cycleId: '',
          });
        })
        .finally(() => {
          setIsLoadingDeleteInfo(false);
        });
    }
  }, [modalData.mode, recordId, modalData.vehicleId]);

  const handleSave = async () => {
    const items = [{
      // Для создания нового интервала timestamp не отправляем - бэкенд сам проставит текущее время
      ...(modalData.mode === 'create' ? {} : {
        timestamp: new Date(formData.timestamp).toISOString(),
      }),
      system_name: formData.system_name,
      system_status: formData.system_status,
      ...(modalData.mode === 'edit' && recordId ? {
        id: recordId,
      } : {}),
    }];

    await onSave({ items });
  };

  const handleDelete = async () => {
    console.log('handleDelete called', { recordId, deleteConfirm, modalData });
    if (modalData.mode === 'delete' && modalData.segment?.recordId) {
      console.log('Calling onDelete', modalData.segment.recordId, { confirm: deleteConfirm });
      try {
        await onDelete(modalData.segment.recordId, { confirm: deleteConfirm });
        console.log('onDelete completed successfully');
      } catch (error) {
        console.error('onDelete failed', error);
      }
    } else {
      console.warn('Cannot delete: missing recordId or wrong mode', { recordId, modalData });
    }
  };

  const getTitle = () => {
    switch (modalData.mode) {
      case 'create':
        return 'Создать новый интервал';
      case 'edit':
        return 'Редактировать интервал';
      case 'delete':
        return 'Удалить интервал';
      default:
        return '';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg bg-dark-card p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">{getTitle()}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {modalData.mode === 'delete' ? (
          <div className="space-y-4">
            <p className="text-gray-300">
              {isLoadingDeleteInfo
                ? 'Проверка последствий удаления...'
                : deleteInfo?.confirmationMessage || 'Вы уверены, что хотите удалить этот интервал?'
              }
            </p>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="confirm-delete"
                checked={deleteConfirm}
                onChange={(e) => setDeleteConfirm(e.target.checked)}
                disabled={isLoadingDeleteInfo}
                className="rounded border-gray-600 bg-dark-bg text-primary-orange focus:border-primary-orange focus:ring-primary-orange disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <label htmlFor="confirm-delete" className="text-sm text-gray-300">
                Подтвердить удаление
              </label>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Поле timestamp скрыто при создании нового интервала */}
            {modalData.mode !== 'create' && (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Время начала
                </label>
                <input
                  type="datetime-local"
                  value={formData.timestamp}
                  onChange={(e) =>
                    setFormData(prev => ({
                      ...prev,
                      timestamp: e.target.value,
                    }))
                  }
                  className="w-full rounded-lg border border-dark-border bg-dark-bg px-3 py-2 text-white ring-primary-orange/30 focus:border-primary-orange focus:outline-none focus:ring-2"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Состояние
              </label>
              <select
                value={formData.system_name}
                onChange={(e) =>
                  setFormData(prev => ({ ...prev, system_name: e.target.value as VehicleState }))
                }
                className="w-full rounded-lg border border-dark-border bg-dark-bg px-3 py-2 text-white ring-primary-orange/30 focus:border-primary-orange focus:outline-none focus:ring-2"
              >
                {Object.entries(STATE_META).map(([state, meta]) => (
                  <option key={state} value={state}>
                    {meta.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="system-status"
                checked={formData.system_status}
                onChange={(e) =>
                  setFormData(prev => ({ ...prev, system_status: e.target.checked }))
                }
                className="rounded border-gray-600 bg-dark-bg text-primary-orange focus:border-primary-orange focus:ring-primary-orange"
              />
              <label htmlFor="system-status" className="text-sm text-gray-300">
                Системный статус (валидация переходов)
              </label>
            </div>
          </div>
        )}

        <div className="mt-6 flex gap-3">
          {modalData.mode === 'edit' && (
            <button
              onClick={() => {
                console.log('Switching to delete mode', modalData);
                // Переход в режим удаления
                onSwitchMode({
                  mode: 'delete',
                  segment: modalData.segment,
                  vehicleId: modalData.vehicleId,
                });
              }}
              className="flex-1 rounded-lg border border-red-600 bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-600/90 focus:outline-none focus:ring-2 focus:ring-red-600/50"
            >
              <Trash2 className="inline h-4 w-4 mr-2" />
              Удалить
            </button>
          )}

          <button
            onClick={onClose}
            className="rounded-lg border border-dark-border bg-dark-bg px-4 py-2 text-sm font-medium text-gray-300 transition-colors hover:bg-dark-border focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            Отмена
          </button>

          <button
            onClick={modalData.mode === 'delete' ? handleDelete : handleSave}
            disabled={isLoading || isLoadingDeleteInfo || (modalData.mode === 'delete' && !deleteConfirm)}
            className="rounded-lg border border-primary-orange bg-primary-orange px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-orange/90 focus:outline-none focus:ring-2 focus:ring-primary-orange/50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <Loader2 className="inline h-4 w-4 animate-spin" />
            ) : modalData.mode === 'delete' ? (
              'Удалить'
            ) : modalData.mode === 'create' ? (
              <>
                <Plus className="inline h-4 w-4 mr-2" />
                Создать
              </>
            ) : (
              <>
                <Edit className="inline h-4 w-4 mr-2" />
                Сохранить
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
