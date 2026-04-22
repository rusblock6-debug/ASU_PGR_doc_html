import { useQuery, useQueries, useMutation, useQueryClient } from '@tanstack/react-query';
import { routeSummaryApi, placesApi, shiftTasksApi, vehiclesApi, statusesApi } from '../api/client';
import { Loader2, ArrowDown, Truck, RefreshCw, X, ChevronDown, ChevronUp } from 'lucide-react';
import type {
  Place,
  RouteSummaryItem,
  RouteTemplateResponse,
  RouteTask,
  RouteTaskBulkUpsertItem,
  ShiftTaskBulkUpsertItem,
} from '../types';
import { Link } from 'react-router-dom';
import { useMemo, useState, useCallback, useEffect } from 'react';

function RoutesOverview() {
  const queryClient = useQueryClient();

  // Выбранная техника для переназначения: { vehicleId, fromRouteKey }
  const [selectedVehicle, setSelectedVehicle] = useState<{
    vehicleId: number;
    fromPlaceA: number;
    fromPlaceB: number;
  } | null>(null);

  const {
    data: summaryData,
    isLoading: summaryLoading,
    error: summaryError,
  } = useQuery({
    queryKey: ['route-summary'],
    queryFn: routeSummaryApi.get,
    refetchInterval: 15000,
  });

  const { data: unusedData } = useQuery({
    queryKey: ['route-summary', 'unused-vehicles'],
    queryFn: routeSummaryApi.getUnusedVehicles,
    refetchInterval: 15000,
  });

  const { data: vehiclesListData } = useQuery({
    queryKey: ['vehicles', 'list'],
    queryFn: () => vehiclesApi.list(),
    staleTime: 60_000,
  });

  const { data: statusesData } = useQuery({
    queryKey: ['statuses'],
    queryFn: () => statusesApi.list(),
    staleTime: 60_000,
  });

  const statusBySystemName = useMemo(() => {
    const map = new Map<string, { color: string; is_work_status: boolean }>();
    for (const s of statusesData?.items ?? []) {
      map.set(s.system_name, { color: s.color, is_work_status: s.is_work_status });
    }
    return map;
  }, [statusesData?.items]);

  const [liveVehicleState, setLiveVehicleState] = useState<Record<number, string>>({});

  useEffect(() => {
    const source = new EventSource('/api/events/stream/all');
    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload?.event_type === 'state_transition' && payload.vehicle_id != null && payload.state != null) {
          const vehicleId = Number(payload.vehicle_id);
          if (!Number.isNaN(vehicleId)) {
            setLiveVehicleState((prev) => ({ ...prev, [vehicleId]: String(payload.state) }));
          }
        }
      } catch {
        // ignore parse errors
      }
    };
    source.onerror = () => {
      source.close();
    };
    return () => source.close();
  }, []);

  const vehicleNameById = useMemo(() => {
    const map: Record<number, string> = {};
    for (const v of vehiclesListData?.items ?? []) {
      map[v.id] = v.name ?? `#${v.id}`;
    }
    return map;
  }, [vehiclesListData?.items]);

  const idleIdsFromLive = useMemo(() => {
    const noTask = unusedData?.no_task ?? [];
    const backendIdle = new Set(unusedData?.idle ?? []);
    return noTask.filter((id) => {
      const state = liveVehicleState[id];
      if (state !== undefined) {
        const status = statusBySystemName.get(state);
        return status ? !status.is_work_status : false;
      }
      return backendIdle.has(id);
    });
  }, [unusedData?.no_task, unusedData?.idle, liveVehicleState, statusBySystemName]);

  // Собираем уникальные place_id из маршрутов
  const uniquePlaceIds = useMemo(() => {
    if (!summaryData?.routes) return [];
    const ids = new Set<number>();
    for (const route of summaryData.routes) {
      ids.add(route.place_a_id);
      ids.add(route.place_b_id);
    }
    return Array.from(ids);
  }, [summaryData?.routes]);

  // Запрашиваем каждое место по ID параллельно
  const placeQueries = useQueries({
    queries: uniquePlaceIds.map((placeId) => ({
      queryKey: ['places', placeId],
      queryFn: () => placesApi.get(placeId),
      enabled: uniquePlaceIds.length > 0,
      staleTime: 30000,
    })),
  });

  const placesMap: Record<number, Place> = useMemo(() => {
    const map: Record<number, Place> = {};
    placeQueries.forEach((query, index) => {
      if (query.data) {
        map[uniquePlaceIds[index]] = query.data;
      }
    });
    return map;
  }, [placeQueries, uniquePlaceIds]);

  const getPlaceName = (placeId: number): string => {
    return placesMap[placeId]?.name ?? `#${placeId}`;
  };

  const getPlaceStock = (placeId: number): number | undefined => {
    return placesMap[placeId]?.current_stock;
  };

  // Состояние модалки создания/редактирования маршрута
  const [isRouteModalOpen, setIsRouteModalOpen] = useState(false);
  const [routeModalMode, setRouteModalMode] = useState<'create' | 'edit'>('create');
  const [routeForEdit, setRouteForEdit] = useState<{ placeA: number; placeB: number } | null>(
    null,
  );

  // pending-назначения и «полупрозрачность» берём с бэка через route_summary/unused-vehicles.

  // Модалка создания наряд-задания для маршрута, у которого ещё нет НЗ.
  const [createRouteTaskContext, setCreateRouteTaskContext] = useState<{
    vehicleId: number;
    sourceKind: 'ROUTE' | 'NO_TASK' | 'GARAGE';
    fromPlaceA: number | null;
    fromPlaceB: number | null;
    sourceGaragePlaceId: number | null;
    targetPlaceA: number;
    targetPlaceB: number;
  } | null>(null);

  const {
    data: placesListData,
    isLoading: placesListLoading,
    error: placesListError,
  } = useQuery({
    queryKey: ['places', 'all'],
    queryFn: () => placesApi.list({ is_active: true, limit: 1000 }),
    staleTime: 60_000,
  });

  const allPlaces: Place[] = placesListData?.items ?? [];
  const loadingPlaces = allPlaces.filter((p) => p.type === 'load');
  const unloadingPlaces = allPlaces.filter((p) => p.type === 'unload');
  const parkPlaces = allPlaces.filter((p) => p.type === 'park');

  const assignmentMutation = useMutation({
    mutationFn: routeSummaryApi.createAssignment,
    onSuccess: () => {
      setSelectedVehicle(null);
      queryClient.invalidateQueries({ queryKey: ['route-summary'] });
      queryClient.invalidateQueries({ queryKey: ['route-summary', 'unused-vehicles'] });
    },
    // error: ValueError с detail, variables: DispatcherAssignmentCreateRequest
    onError: (error: any, variables: any) => {
      const detail = error?.response?.data?.detail;
      if (
        detail === 'Target route_task for vehicle not found' &&
        variables &&
        summaryData?.shift_date &&
        summaryData?.shift_num != null
      ) {
        setCreateRouteTaskContext({
          vehicleId: Number(variables.vehicle_id),
          sourceKind: variables.source_kind,
          fromPlaceA: variables.source_route_place_a_id ?? null,
          fromPlaceB: variables.source_route_place_b_id ?? null,
          sourceGaragePlaceId: variables.source_garage_place_id ?? null,
          targetPlaceA: variables.target_route_place_a_id ?? 0,
          targetPlaceB: variables.target_route_place_b_id ?? 0,
        });
        return;
      }
      alert(detail || 'Не удалось создать назначение');
    },
  });

  const rejectRouteTaskMutation = useMutation({
    mutationFn: routeSummaryApi.rejectRouteTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['route-summary'] });
      queryClient.invalidateQueries({ queryKey: ['route-summary', 'unused-vehicles'] });
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail;
      alert(detail || 'Не удалось отклонить наряд-задание');
    },
  });

  const handleVehicleClick = useCallback(
    (vehicleId: number, placeA: number, placeB: number) => {
      if (
        selectedVehicle?.vehicleId === vehicleId &&
        selectedVehicle.fromPlaceA === placeA &&
        selectedVehicle.fromPlaceB === placeB
      ) {
        setSelectedVehicle(null);
      } else {
        setSelectedVehicle({ vehicleId, fromPlaceA: placeA, fromPlaceB: placeB });
      }
    },
    [selectedVehicle],
  );

  const handleRouteClick = useCallback(
    (targetPlaceA: number, targetPlaceB: number) => {
      if (!selectedVehicle) return;
      if (
        selectedVehicle.fromPlaceA === targetPlaceA &&
        selectedVehicle.fromPlaceB === targetPlaceB
      ) {
        return;
      }
      assignmentMutation.mutate({
        vehicle_id: selectedVehicle.vehicleId,
        source_kind: 'ROUTE',
        source_route_place_a_id: selectedVehicle.fromPlaceA,
        source_route_place_b_id: selectedVehicle.fromPlaceB,
        target_kind: 'ROUTE',
        target_route_place_a_id: targetPlaceA,
        target_route_place_b_id: targetPlaceB,
      });
    },
    [selectedVehicle, assignmentMutation],
  );

  const handleDropOnRoute = useCallback(
    (dragData: DragData, targetPlaceA: number, targetPlaceB: number) => {
      if (
        dragData.from.kind === 'route' &&
        dragData.from.placeA === targetPlaceA &&
        dragData.from.placeB === targetPlaceB
      ) {
        return;
      }
      const sourceKind =
        dragData.from.kind === 'route'
          ? 'ROUTE'
          : dragData.from.kind === 'no_task'
            ? 'NO_TASK'
            : 'GARAGE';

      assignmentMutation.mutate({
        vehicle_id: dragData.vehicleId,
        source_kind: sourceKind,
        source_route_place_a_id: dragData.from.kind === 'route' ? dragData.from.placeA : null,
        source_route_place_b_id: dragData.from.kind === 'route' ? dragData.from.placeB : null,
        source_garage_place_id: dragData.from.kind === 'garage' ? dragData.from.garagePlaceId : null,
        target_kind: 'ROUTE',
        target_route_place_a_id: targetPlaceA,
        target_route_place_b_id: targetPlaceB,
      });
    },
    [assignmentMutation],
  );

  const handleRejectToNoTask = useCallback(
    (dragData: DragData) => {
      if (dragData.from.kind !== 'route') return;
      rejectRouteTaskMutation.mutate({
        vehicle_id: dragData.vehicleId,
        place_a_id: dragData.from.placeA,
        place_b_id: dragData.from.placeB,
      });
    },
    [rejectRouteTaskMutation],
  );

  const handleAssignToGarage = useCallback(
    (dragData: DragData, garagePlaceId: number) => {
      // Запрещаем перемещение no_task <-> garage
      if (dragData.from.kind !== 'route') return;
      assignmentMutation.mutate({
        vehicle_id: dragData.vehicleId,
        source_kind: 'ROUTE',
        source_route_place_a_id: dragData.from.placeA,
        source_route_place_b_id: dragData.from.placeB,
        target_kind: 'GARAGE',
        target_garage_place_id: garagePlaceId,
      });
    },
    [assignmentMutation],
  );

  const handleCancelSelection = useCallback(() => {
    setSelectedVehicle(null);
  }, []);

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['route-summary'] });
    queryClient.invalidateQueries({ queryKey: ['places'] });
    queryClient.invalidateQueries({ queryKey: ['route-summary', 'unused-vehicles'] });
  };

  const createRouteMutation = useMutation<
    RouteTemplateResponse,
    any,
    { placeA: number; placeB: number }
  >({
    mutationFn: ({ placeA, placeB }) =>
      routeSummaryApi.createRoute({
        place_a_id: placeA,
        place_b_id: placeB,
      }),
    onSuccess: (data) => {
      if (!data.success) {
        alert(data.message || 'Не удалось создать маршрут');
        return;
      }
      setIsRouteModalOpen(false);
      setRouteForEdit(null);
      queryClient.invalidateQueries({ queryKey: ['route-summary'] });
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail;
      alert(detail || 'Не удалось создать маршрут');
    },
  });

  const updateRouteMutation = useMutation<
    RouteTemplateResponse,
    any,
    { fromPlaceA: number; fromPlaceB: number; toPlaceA: number; toPlaceB: number }
  >({
    mutationFn: ({ fromPlaceA, fromPlaceB, toPlaceA, toPlaceB }) =>
      routeSummaryApi.updateRoute({
        from_place_a_id: fromPlaceA,
        from_place_b_id: fromPlaceB,
        to_place_a_id: toPlaceA,
        to_place_b_id: toPlaceB,
      }),
    onSuccess: (data) => {
      if (!data.success) {
        alert(data.message || 'Не удалось обновить маршрут');
        return;
      }
      setIsRouteModalOpen(false);
      setRouteForEdit(null);
      queryClient.invalidateQueries({ queryKey: ['route-summary'] });
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail;
      alert(detail || 'Не удалось обновить маршрут');
    },
  });

  const handleOpenCreateRoute = () => {
    setRouteModalMode('create');
    setRouteForEdit(null);
    setIsRouteModalOpen(true);
  };

  const handleOpenEditRoute = useCallback((placeA: number, placeB: number) => {
    setRouteModalMode('edit');
    setRouteForEdit({ placeA, placeB });
    setIsRouteModalOpen(true);
  }, []);

  if (summaryLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-dark-bg text-white">
        <Loader2 className="w-8 h-8 animate-spin text-primary-orange" />
        <span className="ml-3 text-lg">Загрузка маршрутов...</span>
      </div>
    );
  }

  if (summaryError) {
    return (
      <div className="flex items-center justify-center h-screen bg-dark-bg text-red-400">
        <p>Ошибка загрузки: {String(summaryError)}</p>
      </div>
    );
  }

  const routes = summaryData?.routes ?? [];

  return (
    <div className="min-h-screen bg-dark-bg text-white flex flex-col">
      {/* Header */}
      <header className="border-b border-dark-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="text-gray-400 hover:text-white text-sm transition-colors"
          >
            &larr; Назад
          </Link>
          <h1 className="text-xl font-semibold">Маршруты</h1>
          {summaryData?.shift_date && (
            <span className="text-sm text-gray-400">
              Смена {summaryData.shift_num} &middot; {summaryData.shift_date}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {/* Индикатор выбранной техники */}
          {selectedVehicle && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-primary-orange/20 border border-primary-orange/40 text-sm text-primary-orange">
              <Truck className="w-4 h-4" />
              <span>ID {selectedVehicle.vehicleId} — выберите маршрут</span>
              <button
                onClick={handleCancelSelection}
                className="ml-1 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}
          <button
            onClick={handleOpenCreateRoute}
            className="flex items-center gap-2 px-3 py-1.5 rounded bg-primary-orange text-sm text-black font-medium hover:bg-orange-400 transition-colors"
          >
            Создать
          </button>
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-3 py-1.5 rounded bg-dark-card border border-dark-border
                       hover:bg-dark-hover transition-colors text-sm text-gray-300"
          >
            <RefreshCw className="w-4 h-4" />
            Обновить
          </button>
        </div>
      </header>

      {/* Main content + Unused equipment panel */}
      <div className="flex flex-1 gap-6 p-6">
        {/* Routes grid */}
        {routes.length === 0 ? (
          <div className="flex items-center justify-center flex-1 h-[60vh] text-gray-500 text-lg">
            Нет активных маршрутов для текущей смены
          </div>
        ) : (
          <div className="flex gap-6 overflow-x-auto pb-8 flex-1 min-w-0">
            {routes.map((route, idx) => {
            const isSourceRoute =
              selectedVehicle !== null &&
              selectedVehicle.fromPlaceA === route.place_a_id &&
              selectedVehicle.fromPlaceB === route.place_b_id;
            const isTargetCandidate = selectedVehicle !== null && !isSourceRoute;

            return (
              <RouteCard
                key={`${route.place_a_id}-${route.place_b_id}`}
                route={route}
                index={idx + 1}
                placeAName={getPlaceName(route.place_a_id)}
                placeBName={getPlaceName(route.place_b_id)}
                placeAStock={getPlaceStock(route.place_a_id)}
                placeBStock={getPlaceStock(route.place_b_id)}
                selectedVehicleId={selectedVehicle?.vehicleId ?? null}
                isSourceRoute={isSourceRoute}
                isTargetCandidate={isTargetCandidate}
                isReassigning={assignmentMutation.isPending}
                getVehicleColor={(id) => {
                  const state = liveVehicleState[id];
                  return state ? statusBySystemName.get(state)?.color ?? undefined : undefined;
                }}
                onVehicleClick={handleVehicleClick}
                onRouteClick={handleRouteClick}
                onDropOnRoute={handleDropOnRoute}
                onEditRoute={handleOpenEditRoute}
              />
            );
          })}
          </div>
        )}

        <UnusedEquipmentPanel
          noTaskIds={unusedData?.no_task ?? []}
          parkPlaces={parkPlaces}
          garages={unusedData?.garages ?? {}}
          pendingGarages={unusedData?.pending_garages ?? {}}
          idleIds={idleIdsFromLive}
          getVehicleName={(id) => vehicleNameById[id] ?? `#${id}`}
          getVehicleColor={(id) => {
            const state = liveVehicleState[id];
            if (!state) return undefined;
            return statusBySystemName.get(state)?.color ?? undefined;
          }}
          onDropOnNoTask={handleRejectToNoTask}
          onDropOnGarage={handleAssignToGarage}
        />
      </div>

      <RouteEditModal
        isOpen={isRouteModalOpen}
        mode={routeModalMode}
        initialPlaceAId={routeForEdit?.placeA ?? null}
        initialPlaceBId={routeForEdit?.placeB ?? null}
        loadingPlaces={loadingPlaces}
        unloadingPlaces={unloadingPlaces}
        isSubmitting={createRouteMutation.isPending || updateRouteMutation.isPending}
        placesLoading={placesListLoading}
        placesError={placesListError}
        onSubmit={(placeAId, placeBId) => {
          if (routeModalMode === 'create') {
            createRouteMutation.mutate({ placeA: placeAId, placeB: placeBId });
          } else if (routeForEdit) {
            updateRouteMutation.mutate({
              fromPlaceA: routeForEdit.placeA,
              fromPlaceB: routeForEdit.placeB,
              toPlaceA: placeAId,
              toPlaceB: placeBId,
            });
          }
        }}
        onClose={() => {
          if (!createRouteMutation.isPending && !updateRouteMutation.isPending) {
            setIsRouteModalOpen(false);
            setRouteForEdit(null);
          }
        }}
      />

      {createRouteTaskContext && summaryData?.shift_date != null && summaryData?.shift_num != null && (
        <CreateRouteTaskModal
          isOpen={!!createRouteTaskContext}
          vehicleId={createRouteTaskContext.vehicleId}
          targetPlaceA={createRouteTaskContext.targetPlaceA}
          targetPlaceB={createRouteTaskContext.targetPlaceB}
          shiftDate={summaryData.shift_date}
          shiftNum={summaryData.shift_num}
          onSuccess={() => {
            if (createRouteTaskContext) {
              // После создания НЗ сразу создаём pending-назначение, чтобы техника
              // отобразилась на новом маршруте полупрозрачной.
              assignmentMutation.mutate({
                vehicle_id: createRouteTaskContext.vehicleId,
                source_kind: createRouteTaskContext.sourceKind,
                source_route_place_a_id:
                  createRouteTaskContext.sourceKind === 'ROUTE' ? createRouteTaskContext.fromPlaceA : null,
                source_route_place_b_id:
                  createRouteTaskContext.sourceKind === 'ROUTE' ? createRouteTaskContext.fromPlaceB : null,
                source_garage_place_id:
                  createRouteTaskContext.sourceKind === 'GARAGE'
                    ? createRouteTaskContext.sourceGaragePlaceId
                    : null,
                target_kind: 'ROUTE',
                target_route_place_a_id: createRouteTaskContext.targetPlaceA,
                target_route_place_b_id: createRouteTaskContext.targetPlaceB,
              });
            }
            queryClient.invalidateQueries({ queryKey: ['route-summary'] });
            queryClient.invalidateQueries({ queryKey: ['route-summary', 'unused-vehicles'] });
            setCreateRouteTaskContext(null);
            setSelectedVehicle(null);
          }}
          onClose={() => setCreateRouteTaskContext(null)}
        />
      )}
    </div>
  );
}

export type DragData =
  | { vehicleId: number; from: { kind: 'route'; placeA: number; placeB: number } }
  | { vehicleId: number; from: { kind: 'no_task' } }
  | { vehicleId: number; from: { kind: 'garage'; garagePlaceId: number } };

function parseDragData(raw: string): DragData | null {
  try {
    const d = JSON.parse(raw);
    if (typeof d?.vehicleId !== 'number') return null;
    if (d?.from?.kind === 'route' && typeof d.from.placeA === 'number' && typeof d.from.placeB === 'number') return d as DragData;
    if (d?.from?.kind === 'no_task') return d as DragData;
    if (d?.from?.kind === 'garage' && typeof d.from.garagePlaceId === 'number') return d as DragData;
    return null;
  } catch {
    return null;
  }
}

interface UnusedEquipmentPanelProps {
  noTaskIds: number[];
  parkPlaces: Place[];
  garages: Record<number, number[]>;
  pendingGarages: Record<number, number[]>;
  idleIds: number[];
  getVehicleName: (id: number) => string;
  getVehicleColor?: (id: number) => string | undefined;
  onDropOnNoTask?: (data: DragData) => void;
  onDropOnGarage?: (data: DragData, garagePlaceId: number) => void;
}

function UnusedEquipmentPanel({
  noTaskIds,
  parkPlaces,
  garages,
  pendingGarages,
  idleIds,
  getVehicleName,
  getVehicleColor,
  onDropOnNoTask,
  onDropOnGarage,
}: UnusedEquipmentPanelProps) {
  const [garageOpen, setGarageOpen] = useState(true);
  const [noTaskOpen, setNoTaskOpen] = useState(true);
  const [idleOpen, setIdleOpen] = useState(true);

  const totalCount = useMemo(() => {
    const garageIds = Object.values(garages ?? {}).flat();
    const pendingIds = Object.values(pendingGarages ?? {}).flat();
    const set = new Set<number>([...noTaskIds, ...idleIds, ...garageIds, ...pendingIds]);
    return set.size;
  }, [noTaskIds, idleIds, garages, pendingGarages]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const renderVehicleList = (
    ids: number[],
    options?: { draggable?: boolean; isPending?: (id: number) => boolean; dragKind?: 'no_task' | 'garage'; garagePlaceId?: number },
  ) => (
    <div className="flex flex-wrap gap-3 mt-2">
      {ids.map((id) => {
        const color = getVehicleColor?.(id);
        const isPending = options?.isPending?.(id);
        return (
          <div
            key={id}
            className={`flex flex-col items-center gap-1 min-w-[60px] ${options?.draggable ? 'cursor-grab active:cursor-grabbing' : ''}`}
            draggable={options?.draggable}
            onDragStart={options?.draggable ? (e) => {
              const from =
                options?.dragKind === 'garage' && options?.garagePlaceId != null
                  ? { kind: 'garage' as const, garagePlaceId: options.garagePlaceId }
                  : { kind: 'no_task' as const };
              e.dataTransfer.setData('application/json', JSON.stringify({ vehicleId: id, from }));
              e.dataTransfer.effectAllowed = 'move';
            } : undefined}
          >
            <Truck
              className={`w-8 h-8 flex-shrink-0 ${color ? '' : 'text-primary-orange'} ${isPending ? 'opacity-50' : ''}`}
              style={color ? { color } : undefined}
            />
            <span className="text-xs text-white truncate max-w-[80px] text-center">
              {getVehicleName(id)}
            </span>
          </div>
        );
      })}
    </div>
  );

  return (
    <div className="flex-shrink-0 w-72 rounded-xl bg-dark-card border border-dark-border overflow-hidden flex flex-col max-h-[calc(100vh-8rem)]">
      <div className="px-4 py-3 border-b border-dark-border flex items-center justify-between">
        <h2 className="text-base font-semibold text-white">Незадействованная техника</h2>
        <span className="text-sm text-gray-400">{totalCount}</span>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {/* Гаражи (places.type=park) */}
        <div className="mb-2">
          <button
            type="button"
            className="w-full flex items-center justify-between py-2 px-2 rounded hover:bg-dark-hover text-left text-white"
            onClick={() => setGarageOpen((v) => !v)}
          >
            <span className="text-sm font-medium">Гаражи</span>
            <span className="text-gray-400 text-sm mr-1">{parkPlaces.length}</span>
            {garageOpen ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>
          {garageOpen && (
            <div className="space-y-2 mt-1">
              {parkPlaces.map((park) => {
                const garageIds = (garages as any)?.[park.id] ?? (garages as any)?.[String(park.id)] ?? [];
                const pendingIds = (pendingGarages as any)?.[park.id] ?? (pendingGarages as any)?.[String(park.id)] ?? [];
                const display = [...garageIds, ...pendingIds.filter((id: number) => !garageIds.includes(id))];
                const pendingSet = new Set<number>(pendingIds);
                return (
                  <div key={park.id} className="px-2 py-2 rounded border border-dark-border/60 bg-neutral-900/20">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-gray-300 truncate">{park.name}</span>
                      <span className="text-xs text-gray-500">{display.length}</span>
                    </div>
                    <div
                      onDragOver={handleDragOver}
                      onDrop={(e) => {
                        e.preventDefault();
                        const data = parseDragData(e.dataTransfer.getData('application/json'));
                        if (data && data.from.kind === 'route') onDropOnGarage?.(data, park.id);
                      }}
                    >
                      {renderVehicleList(display, {
                        draggable: true,
                        dragKind: 'garage',
                        garagePlaceId: park.id,
                        isPending: (id) => pendingSet.has(id),
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
        {/* Нет задания */}
        <div className="mb-2">
          <button
            type="button"
            className="w-full flex items-center justify-between py-2 px-2 rounded hover:bg-dark-hover text-left text-white"
            onClick={() => setNoTaskOpen((v) => !v)}
          >
            <span className="text-sm font-medium">Нет задания</span>
            <span className="text-gray-400 text-sm mr-1">{noTaskIds.length}</span>
            {noTaskOpen ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>
          {noTaskOpen && (
            <div
              onDragOver={handleDragOver}
              onDrop={(e) => {
                e.preventDefault();
                const data = parseDragData(e.dataTransfer.getData('application/json'));
                if (data && data.from.kind === 'route') onDropOnNoTask?.(data);
              }}
            >
              {renderVehicleList(noTaskIds, { draggable: true, dragKind: 'no_task' })}
            </div>
          )}
        </div>
        {/* В простое */}
        <div className="mb-2">
          <button
            type="button"
            className="w-full flex items-center justify-between py-2 px-2 rounded hover:bg-dark-hover text-left text-white"
            onClick={() => setIdleOpen((v) => !v)}
          >
            <span className="text-sm font-medium">В простое</span>
            <span className="text-gray-400 text-sm mr-1">{idleIds.length}</span>
            {idleOpen ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>
          {idleOpen && renderVehicleList(idleIds, { draggable: true, dragKind: 'no_task' })}
        </div>
      </div>
    </div>
  );
}

interface CreateRouteTaskModalProps {
  isOpen: boolean;
  vehicleId: number;
  targetPlaceA: number;
  targetPlaceB: number;
  shiftDate: string;
  shiftNum: number;
  onSuccess: () => void;
  onClose: () => void;
}

function CreateRouteTaskModal({
  isOpen,
  vehicleId,
  targetPlaceA,
  targetPlaceB,
  shiftDate,
  shiftNum,
  onSuccess,
  onClose,
}: CreateRouteTaskModalProps) {
  const [volume, setVolume] = useState<string>('');
  const [weight, setWeight] = useState<string>('');
  const [trips, setTrips] = useState<string>('1');
  const [comment, setComment] = useState<string>('');

  const { data: listData, isLoading: shiftLoading } = useQuery({
    queryKey: ['shift-tasks', vehicleId, shiftDate, shiftNum],
    queryFn: () =>
      shiftTasksApi.list({
        shift_date: shiftDate,
        vehicle_ids: [vehicleId],
        shift_num: shiftNum,
        size: 5,
      }),
    enabled: isOpen,
  });

  const bulkUpsertMutation = useMutation({
    mutationFn: (payload: { items: ShiftTaskBulkUpsertItem[] }) =>
      shiftTasksApi.bulkUpsert(payload),
    onSuccess: (_data, _variables) => {
      onSuccess();
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail;
      alert(detail ?? 'Не удалось создать наряд-задание');
    },
  });

  const shiftTask = listData?.items?.[0];

  const handleSubmit = () => {
    if (!shiftTask?.id) return;
    const routeTasks = shiftTask.route_tasks ?? [];
    const maxOrder = routeTasks.length ? Math.max(...routeTasks.map((r) => r.route_order ?? 0)) : -1;
    const updatedRouteTasks: RouteTaskBulkUpsertItem[] = routeTasks.map((rt: RouteTask) => ({
      id: rt.id ?? undefined,
      route_order: rt.route_order,
      shift_task_id: shiftTask.id,
      place_a_id: rt.place_a_id,
      place_b_id: rt.place_b_id,
      type_task: (rt.type_task ?? 'LOADING_TRANSPORT_GM').toUpperCase().replace(/-/g, '_'),
      planned_trips_count: rt.planned_trips_count ?? 1,
      actual_trips_count: rt.actual_trips_count ?? 0,
      status: (rt.status ?? 'EMPTY').toUpperCase(),
      volume: rt.volume ?? undefined,
      weight: rt.weight ?? undefined,
      message: rt.message ?? undefined,
    }));
    const plannedTripsNum = parseInt(trips, 10) || 1;
    const volumeNum = volume === '' ? undefined : parseFloat(volume);
    const weightNum = weight === '' ? undefined : parseFloat(weight);
    updatedRouteTasks.push({
      route_order: maxOrder + 1,
      shift_task_id: shiftTask.id,
      place_a_id: targetPlaceA,
      place_b_id: targetPlaceB,
      type_task: 'LOADING_TRANSPORT_GM',
      planned_trips_count: plannedTripsNum,
      actual_trips_count: 0,
      status: 'SENT',
      volume: volumeNum ?? undefined,
      weight: weightNum ?? undefined,
      message: comment.trim() || undefined,
    });

    bulkUpsertMutation.mutate({
      items: [
        {
          id: shiftTask.id,
          work_regime_id: shiftTask.work_regime_id,
          vehicle_id: shiftTask.vehicle_id,
          shift_date: shiftTask.shift_date,
          shift_num: shiftTask.shift_num ?? shiftNum,
          priority: shiftTask.priority ?? 0,
          status: shiftTask.status,
          route_tasks: updatedRouteTasks,
        },
      ],
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-md rounded-2xl bg-dark-card border border-dark-border shadow-xl p-6">
        <div className="flex items-start justify-between mb-4">
          <h2 className="text-lg font-semibold">Создать наряд-задание</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
            disabled={bulkUpsertMutation.isPending}
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <p className="text-sm text-gray-400 mb-4">
          На маршруте нет наряд-задания. Заполните данные для создания.
        </p>
        {shiftLoading ? (
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Загрузка смены...</span>
          </div>
        ) : !shiftTask ? (
          <div className="text-sm text-red-400">Смена для техники не найдена</div>
        ) : (
          <>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Объем</label>
                <input
                  type="text"
                  inputMode="decimal"
                  className="w-full rounded-lg bg-neutral-800 border border-dark-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-orange/60"
                  value={volume}
                  onChange={(e) => setVolume(e.target.value)}
                  placeholder="Объем"
                  disabled={bulkUpsertMutation.isPending}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Вес</label>
                <input
                  type="text"
                  inputMode="decimal"
                  className="w-full rounded-lg bg-neutral-800 border border-dark-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-orange/60"
                  value={weight}
                  onChange={(e) => setWeight(e.target.value)}
                  placeholder="Вес"
                  disabled={bulkUpsertMutation.isPending}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Рейсы</label>
                <input
                  type="text"
                  inputMode="numeric"
                  className="w-full rounded-lg bg-neutral-800 border border-dark-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-orange/60"
                  value={trips}
                  onChange={(e) => setTrips(e.target.value)}
                  placeholder="Планируемое кол-во рейсов"
                  disabled={bulkUpsertMutation.isPending}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Коммент</label>
                <input
                  type="text"
                  className="w-full rounded-lg bg-neutral-800 border border-dark-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-orange/60"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Комментарий"
                  disabled={bulkUpsertMutation.isPending}
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 rounded-lg text-sm text-gray-300 hover:bg-dark-hover"
                disabled={bulkUpsertMutation.isPending}
              >
                Отмена
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                className="px-4 py-1.5 rounded-lg text-sm font-medium bg-primary-orange text-black hover:bg-orange-400 disabled:opacity-60 disabled:cursor-not-allowed"
                disabled={bulkUpsertMutation.isPending}
              >
                {bulkUpsertMutation.isPending ? 'Отправка...' : 'Отправить'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

interface RouteEditModalProps {
  isOpen: boolean;
  mode: 'create' | 'edit';
  initialPlaceAId: number | null;
  initialPlaceBId: number | null;
  loadingPlaces: Place[];
  unloadingPlaces: Place[];
  isSubmitting: boolean;
  placesLoading: boolean;
  placesError: unknown;
  onSubmit: (placeAId: number, placeBId: number) => void;
  onClose: () => void;
}

function RouteEditModal({
  isOpen,
  mode,
  initialPlaceAId,
  initialPlaceBId,
  loadingPlaces,
  unloadingPlaces,
  isSubmitting,
  placesLoading,
  placesError,
  onSubmit,
  onClose,
}: RouteEditModalProps) {
  const [placeAId, setPlaceAId] = useState<number | ''>(initialPlaceAId ?? '');
  const [placeBId, setPlaceBId] = useState<number | ''>(initialPlaceBId ?? '');

  useEffect(() => {
    if (isOpen) {
      setPlaceAId(initialPlaceAId ?? '');
      setPlaceBId(initialPlaceBId ?? '');
    }
  }, [isOpen, initialPlaceAId, initialPlaceBId]);

  if (!isOpen) {
    return null;
  }

  const handleConfirm = () => {
    if (placeAId === '' || placeBId === '') {
      alert('Выберите ПП и ПР');
      return;
    }
    onSubmit(placeAId, placeBId);
  };

  const title = mode === 'create' ? 'Создать маршрут' : 'Изменить ПП/ПР маршрута';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-md rounded-2xl bg-dark-card border border-dark-border shadow-xl p-6">
        <div className="flex items-start justify-between mb-4">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
            disabled={isSubmitting}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {placesLoading ? (
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Загрузка списка мест...</span>
          </div>
        ) : placesError ? (
          <div className="text-sm text-red-400">Не удалось загрузить список мест</div>
        ) : (
          <>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Место погрузки (ПП)</label>
                <select
                  className="w-full rounded-lg bg-neutral-800 border border-dark-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-orange/60"
                  value={placeAId}
                  onChange={(e) => setPlaceAId(e.target.value ? Number(e.target.value) : '')}
                  disabled={isSubmitting}
                >
                  <option value="">Выберите место погрузки</option>
                  {loadingPlaces.map((place) => (
                    <option key={place.id} value={place.id}>
                      {place.name} (#{place.id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1">Место разгрузки (ПР)</label>
                <select
                  className="w-full rounded-lg bg-neutral-800 border border-dark-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-orange/60"
                  value={placeBId}
                  onChange={(e) => setPlaceBId(e.target.value ? Number(e.target.value) : '')}
                  disabled={isSubmitting}
                >
                  <option value="">Выберите место разгрузки</option>
                  {unloadingPlaces.map((place) => (
                    <option key={place.id} value={place.id}>
                      {place.name} (#{place.id})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                onClick={onClose}
                className="px-3 py-1.5 rounded-lg text-sm text-gray-300 hover:bg-dark-hover"
                disabled={isSubmitting}
              >
                Отмена
              </button>
              <button
                onClick={handleConfirm}
                className="px-4 py-1.5 rounded-lg text-sm font-medium bg-primary-orange text-black hover:bg-orange-400 disabled:opacity-60 disabled:cursor-not-allowed"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Сохранение...' : 'Сохранить'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

interface RouteCardProps {
  route: RouteSummaryItem;
  index: number;
  placeAName: string;
  placeBName: string;
  placeAStock?: number;
  placeBStock?: number;
  selectedVehicleId: number | null;
  isSourceRoute: boolean;
  isTargetCandidate: boolean;
  isReassigning: boolean;
  getVehicleColor?: (vehicleId: number) => string | undefined;
  onVehicleClick: (vehicleId: number, placeA: number, placeB: number) => void;
  onRouteClick: (targetPlaceA: number, targetPlaceB: number) => void;
  onDropOnRoute?: (dragData: DragData, targetPlaceA: number, targetPlaceB: number) => void;
  onEditRoute: (placeA: number, placeB: number) => void;
}

function RouteCard({
  route,
  index,
  placeAName,
  placeBName,
  placeAStock,
  placeBStock,
  selectedVehicleId,
  isSourceRoute,
  isTargetCandidate,
  isReassigning,
  getVehicleColor,
  onVehicleClick,
  onRouteClick,
  onDropOnRoute,
  onEditRoute,
}: RouteCardProps) {
  const activeVehicleIds = new Set(route.active_vehicles);
  const pendingIds = route.pending_vehicles ?? [];
  const displayVehicles: { vehicleId: number; isPending: boolean }[] = [
    ...route.active_vehicles.map((id) => ({ vehicleId: id, isPending: false })),
    ...pendingIds.filter((id) => !activeVehicleIds.has(id)).map((id) => ({ vehicleId: id, isPending: true })),
  ];

  const progress =
    route.volume_plan > 0
      ? Math.min((route.volume_fact / route.volume_plan) * 100, 100)
      : 0;

  const handleCardClick = () => {
    if (isTargetCandidate && !isReassigning) {
      onRouteClick(route.place_a_id, route.place_b_id);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const data = parseDragData(e.dataTransfer.getData('application/json'));
    if (data && onDropOnRoute) onDropOnRoute(data, route.place_a_id, route.place_b_id);
  };

  return (
    <div className="flex-shrink-0 w-56 flex flex-col">
      {/* Route header */}
      <div className="mb-3">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-medium text-gray-300 truncate">
            Маршрут {index}{' '}
            <span className="text-gray-500">
              ({placeAName} - {placeBName})
            </span>
          </p>
          <button
            type="button"
            className="text-[11px] text-gray-400 hover:text-white underline-offset-2 hover:underline"
            onClick={(e) => {
              e.stopPropagation();
              onEditRoute(route.place_a_id, route.place_b_id);
            }}
          >
            Изменить
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-0.5">
          План {route.volume_plan} &nbsp; Факт {route.volume_fact}
        </p>
      </div>

      {/* Route column */}
      <div
        onClick={handleCardClick}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        className={`
          relative flex flex-col bg-dark-card rounded-2xl border overflow-hidden flex-1 min-h-[420px]
          transition-all duration-200
          ${isSourceRoute ? 'border-primary-orange/60 ring-1 ring-primary-orange/30' : ''}
          ${isTargetCandidate ? 'border-green-500/60 cursor-pointer hover:ring-1 hover:ring-green-500/40' : ''}
          ${!isSourceRoute && !isTargetCandidate ? 'border-dark-border' : ''}
          ${isReassigning && isTargetCandidate ? 'opacity-50 pointer-events-none' : ''}
        `}
      >
        {/* Target hint */}
        {isTargetCandidate && (
          <div className="absolute top-2 right-2 z-20 px-2 py-0.5 rounded bg-green-600/80 text-xs text-white">
            Переместить сюда
          </div>
        )}

        {/* Progress bar background */}
        <div
          className="absolute bottom-0 left-0 right-0 bg-primary-orange/10 transition-all duration-500"
          style={{ height: `${progress}%` }}
        />

        {/* ПП (loading place) */}
        <div className="relative z-10 p-4">
          <div className="bg-neutral-700/80 rounded-lg px-4 py-3 text-center">
            <p className="text-lg font-bold">ПП</p>
            <p className="text-sm text-gray-300">
              {placeAName}
              {placeAStock != null && (
                <span className="text-gray-400"> ({placeAStock}т.)</span>
              )}
            </p>
          </div>
        </div>

        {/* Vehicles in progress + pending (полупрозрачные до перехода в «В работе») */}
        <div className="relative z-10 flex-1 flex flex-col justify-center gap-3 px-4 py-2">
          {displayVehicles.length > 0 ? (
            displayVehicles.map(({ vehicleId, isPending }) => {
              const isSelected = selectedVehicleId === vehicleId && isSourceRoute;
              const color = getVehicleColor?.(vehicleId);
              return (
                <button
                  key={vehicleId}
                  type="button"
                  draggable
                  onDragStart={(e) => {
                    e.stopPropagation();
                    e.dataTransfer.setData(
                      'application/json',
                      JSON.stringify({
                        vehicleId,
                        from: { kind: 'route', placeA: route.place_a_id, placeB: route.place_b_id },
                      }),
                    );
                    e.dataTransfer.effectAllowed = 'move';
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    onVehicleClick(vehicleId, route.place_a_id, route.place_b_id);
                  }}
                  className={`
                    flex items-center gap-2 text-sm px-2 py-1.5 rounded-md transition-all text-left cursor-grab active:cursor-grabbing
                    ${isSelected
                      ? 'bg-primary-orange/20 text-primary-orange ring-1 ring-primary-orange/50'
                      : 'text-gray-300 hover:bg-dark-hover cursor-pointer'
                    }
                    ${isPending ? 'opacity-50' : ''}
                  `}
                >
                  <Truck
                    className={`w-5 h-5 flex-shrink-0 ${color ? '' : 'text-primary-orange'}`}
                    style={color ? { color } : undefined}
                  />
                  <span className="truncate">ID {vehicleId}</span>
                </button>
              );
            })
          ) : (
            <div className="flex flex-col items-center text-gray-600 text-xs gap-1">
              <ArrowDown className="w-5 h-5" />
              <span>Нет активной техники</span>
            </div>
          )}
        </div>

        {/* ПР (unloading place) */}
        <div className="relative z-10 p-4 mt-auto">
          <div className="bg-neutral-700/80 rounded-lg px-4 py-3 text-center">
            <p className="text-lg font-bold">ПР</p>
            <p className="text-sm text-gray-300">
              {placeBName}
              {placeBStock != null && (
                <span className="text-gray-400"> ({placeBStock}т.)</span>
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default RoutesOverview;
