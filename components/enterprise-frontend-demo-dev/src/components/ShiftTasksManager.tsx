import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { vehiclesApi, workRegimesApi, placesApi, shiftTasksApi } from '../api/client';
import { Vehicle, ShiftTaskCreate, RouteTask, TASK_TYPES, TaskType } from '../types';
import { 
  Loader2, 
  Plus, 
  Trash2, 
  Save, 
  AlertCircle,
  Truck,
  ArrowRight,
  Weight,
  Package2,
  ChevronDown,
  ChevronUp,
  Send,
} from 'lucide-react';

interface RouteFormData {
  id: string;
  place_a_id: number | null;
  place_b_id: number | null;
  volume: number;
  trips: number;
}

interface VehicleTaskState {
  vehicleId: number;
  isExpanded: boolean;
  taskType: TaskType;
  plannedTotal: number;
  routes: RouteFormData[];
  inputMode: 'volume' | 'trips';
  existingTaskId: string | null;
  isSaved: boolean;
}

export default function ShiftTasksManager() {
  const queryClient = useQueryClient();
  const [vehicleTasks, setVehicleTasks] = useState<Map<number, VehicleTaskState>>(new Map());
  const [globalWorkRegime, setGlobalWorkRegime] = useState<number | null>(null);
  
  // Состояние для выбранной даты смены
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  
  // Используем выбранную дату для смены
  const currentDate = selectedDate;

  // Загрузка данных
  const { data: vehiclesData, isLoading: vehiclesLoading } = useQuery({
    queryKey: ['vehicles', 'active'],
    queryFn: () => vehiclesApi.list({ 
      enterprise_id: 1, 
      is_active: true,
      size: 100,
    }),
  });

  const { data: workRegimesData } = useQuery({
    queryKey: ['work-regimes', 'active'],
    queryFn: () => workRegimesApi.list({ 
      enterprise_id: 1, 
      is_active: true,
      size: 100,
    }),
  });

  const { data: loadingPlaces } = useQuery({
    queryKey: ['places', 'load'],
    queryFn: () => placesApi.list({ 
      type: 'load', 
      is_active: true,
      limit: 100,
    }),
  });

  const { data: unloadingPlaces } = useQuery({
    queryKey: ['places', 'unload'],
    queryFn: () => placesApi.list({ 
      type: 'unload', 
      is_active: true,
      limit: 100,
    }),
  });

  // Получение вместительности кузова
  const getVehicleCapacity = (vehicle: Vehicle | null): number => {
    if (!vehicle) return 30;
    if (vehicle.vehicle_type === 'shas') {
      return vehicle.payload_volume || 30;
    } else if (vehicle.vehicle_type === 'pdm') {
      return vehicle.capacity_volume || 30;
    }
    return 30;
  };

  // Проверка существующих заданий для всех техник
  const { data: allExistingTasks } = useQuery({
    queryKey: ['shift-tasks', 'all', currentDate],
    queryFn: () => shiftTasksApi.list({
      enterprise_id: 1,
      shift_date: currentDate,
      size: 100,
    }),
  });

  // Загрузка существующих заданий при старте
  useEffect(() => {
    if (allExistingTasks && vehiclesData) {
      const newVehicleTasks = new Map(vehicleTasks);
      
      allExistingTasks.items.forEach(task => {
        const vehicle = vehiclesData.items.find(v => v.id === task.vehicle_id);
        if (vehicle && !newVehicleTasks.has(vehicle.id)) {
          const taskTypeKey = Object.keys(TASK_TYPES).find(
            key => TASK_TYPES[key as TaskType] === task.task_name
          ) as TaskType || 'independent';

          const routes = task.route_tasks?.map((rt, idx) => {
            const vehicleCapacity = getVehicleCapacity(vehicle);
            const volume = rt.planned_trips_count * vehicleCapacity;
            
            return {
              id: `route-${idx}-${Date.now()}-${vehicle.id}`,
              place_a_id: rt.place_a_id,
              place_b_id: rt.place_b_id,
              volume: volume,
              trips: rt.planned_trips_count,
            };
          }) || [];

          newVehicleTasks.set(vehicle.id, {
            vehicleId: vehicle.id,
            isExpanded: false,
            taskType: taskTypeKey,
            plannedTotal: 0,
            routes: routes,
            inputMode: 'volume',
            existingTaskId: task.id,
            isSaved: true,
          });
          
          // Устанавливаем глобальный режим работы из первого найденного задания
          if (globalWorkRegime === null) {
            setGlobalWorkRegime(task.work_regime_id);
          }
        }
      });

      setVehicleTasks(newVehicleTasks);
    }
  }, [allExistingTasks, vehiclesData]);

  // Переключение развернутости карточки техники
  const toggleVehicle = (vehicleId: number) => {
    setVehicleTasks(prev => {
      const newMap = new Map(prev);
      const current = newMap.get(vehicleId);
      
      if (current) {
        newMap.set(vehicleId, { ...current, isExpanded: !current.isExpanded });
      } else {
        newMap.set(vehicleId, {
          vehicleId,
          isExpanded: true,
          taskType: 'independent',
          plannedTotal: 0,
          routes: [],
          inputMode: 'volume',
          existingTaskId: null,
          isSaved: false,
        });
      }
      
      return newMap;
    });
  };

  // Обновление состояния техники
  const updateVehicleTask = (vehicleId: number, updates: Partial<VehicleTaskState>) => {
    setVehicleTasks(prev => {
      const newMap = new Map(prev);
      const current = newMap.get(vehicleId);
      if (current) {
        // Если isSaved явно передан в updates, используем его значение
        // Иначе устанавливаем false (при любых изменениях данных)
        const isSaved = 'isSaved' in updates ? (updates.isSaved ?? false) : false;
        newMap.set(vehicleId, { ...current, ...updates, isSaved });
      }
      return newMap;
    });
  };

  // Расчет распределенного объема для техники
  const getDistributedVolume = (routes: RouteFormData[]) => {
    return routes.reduce((sum, route) => sum + (route.volume || 0), 0);
  };

  // Остаток для техники
  const getRemainingVolume = (plannedTotal: number, routes: RouteFormData[]) => {
    return Math.max(0, plannedTotal - getDistributedVolume(routes));
  };

  // Добавление маршрута
  const addRoute = (vehicleId: number) => {
    const current = vehicleTasks.get(vehicleId);
    if (current) {
      const newRoutes = [
        ...current.routes,
        {
          id: `route-${Date.now()}-${vehicleId}`,
          place_a_id: null,
          place_b_id: null,
          volume: 0,
          trips: 0,
        },
      ];
      updateVehicleTask(vehicleId, { routes: newRoutes });
    }
  };

  // Удаление маршрута
  const removeRoute = (vehicleId: number, routeId: string) => {
    const current = vehicleTasks.get(vehicleId);
    if (current) {
      const newRoutes = current.routes.filter(r => r.id !== routeId);
      updateVehicleTask(vehicleId, { routes: newRoutes });
    }
  };

  // Обновление маршрута
  const updateRoute = (vehicleId: number, routeId: string, field: keyof RouteFormData, value: any) => {
    const current = vehicleTasks.get(vehicleId);
    if (!current) return;

    const vehicle = vehiclesData?.items.find(v => v.id === vehicleId);
    const vehicleCapacity = getVehicleCapacity(vehicle || null);
    const remainingVolume = getRemainingVolume(current.plannedTotal, current.routes);

    const newRoutes = current.routes.map(route => {
      if (route.id === routeId) {
        if (field === 'place_a_id' || field === 'place_b_id') {
          return { ...route, [field]: value ? Number(value) : null };
        }

        const updated = { ...route, [field]: value };
        
        if (field === 'volume') {
          const newVolume = Math.max(0, Math.min(value, remainingVolume + route.volume));
          updated.volume = newVolume;
          updated.trips = Math.ceil(newVolume / vehicleCapacity);
        } else if (field === 'trips') {
          const newTrips = Math.max(0, value);
          updated.trips = newTrips;
          updated.volume = newTrips * vehicleCapacity;
          
          const maxVolume = remainingVolume + route.volume;
          if (updated.volume > maxVolume) {
            updated.volume = maxVolume;
            updated.trips = Math.floor(maxVolume / vehicleCapacity);
          }
        }
        
        return updated;
      }
      return route;
    });

    updateVehicleTask(vehicleId, { routes: newRoutes });
  };

  // Сохранение задания (без отправки в MQTT)
  const saveMutation = useMutation({
    mutationFn: async (vehicleId: number) => {
      const current = vehicleTasks.get(vehicleId);
      const vehicle = vehiclesData?.items.find(v => v.id === vehicleId);
      
      if (!current || !vehicle || !globalWorkRegime) {
        throw new Error('Выберите технику и режим работы');
      }

      if (current.routes.length === 0) {
        throw new Error('Добавьте хотя бы один маршрут');
      }

      const invalidRoutes = current.routes.filter(r => 
        r.place_a_id === null || 
        r.place_b_id === null || 
        r.trips === 0
      );
      if (invalidRoutes.length > 0) {
        throw new Error('Заполните все поля маршрутов');
      }

      const routeTasks: RouteTask[] = current.routes.map((route, idx) => ({
        route_order: idx + 1,
        planned_trips_count: route.trips,
        actual_trips_count: 0,
        status: 'pending',
        place_a_id: route.place_a_id || 0,
        place_b_id: route.place_b_id || 0,
      }));

      const taskData: ShiftTaskCreate = {
        work_regime_id: globalWorkRegime,
        vehicle_id: vehicle.id,
        shift_date: currentDate,
        task_name: TASK_TYPES[current.taskType],
        priority: 0,
        status: 'pending',
        route_tasks: routeTasks,
      };

      return { vehicleId, result: await shiftTasksApi.save(taskData) };
    },
    onSuccess: async ({ vehicleId, result }) => {
      // Инвалидируем запросы и ждем их обновления
      await queryClient.invalidateQueries({ queryKey: ['shift-tasks'] });
      
      // Обновляем локальное состояние
      updateVehicleTask(vehicleId, { 
        existingTaskId: result.id, 
        isSaved: true 
      });
      
      // Принудительно перезагружаем данные
      await queryClient.refetchQueries({ queryKey: ['shift-tasks', 'all', currentDate] });
      
      alert('Задание успешно сохранено!');
    },
    onError: (error: any) => {
      alert(`Ошибка: ${error.message || 'Не удалось сохранить задание'}`);
    },
  });

  // Утверждение всех сохраненных заданий
  const approveAllMutation = useMutation({
    mutationFn: async () => {
      const savedTasks = Array.from(vehicleTasks.entries())
        .filter(([_, task]) => task.isSaved && task.existingTaskId);

      if (savedTasks.length === 0) {
        throw new Error('Нет сохраненных заданий для утверждения');
      }

      // Отправляем все задания через обычный create/update для отправки в MQTT
      const results = await Promise.all(
        savedTasks.map(async ([vehicleId, taskState]) => {
          const vehicle = vehiclesData?.items.find(v => v.id === vehicleId);
          if (!vehicle || !globalWorkRegime) return null;

          const routeTasks: RouteTask[] = taskState.routes.map((route, idx) => ({
            route_order: idx + 1,
            planned_trips_count: route.trips,
            actual_trips_count: 0,
            status: 'pending',
            place_a_id: route.place_a_id || 0,
            place_b_id: route.place_b_id || 0,
          }));

          const taskData: ShiftTaskCreate = {
            work_regime_id: globalWorkRegime,
            vehicle_id: vehicle.id,
            shift_date: currentDate,
            task_name: TASK_TYPES[taskState.taskType],
            priority: 0,
            status: 'pending',
            route_tasks: routeTasks,
          };

          // Всегда используем create, так как POST /shift-tasks поддерживает upsert
          // (создание или обновление на основе vehicle_id, shift_date, work_regime_id)
          return await shiftTasksApi.create(taskData);
        })
      );

      return results.filter(r => r !== null);
    },
    onSuccess: async () => {
      // Инвалидируем запросы и ждем их обновления
      await queryClient.invalidateQueries({ queryKey: ['shift-tasks'] });
      
      // Принудительно перезагружаем данные
      await queryClient.refetchQueries({ queryKey: ['shift-tasks', 'all', currentDate] });
      
      alert('Все задания успешно утверждены и отправлены на борт!');
    },
    onError: (error: any) => {
      alert(`Ошибка утверждения: ${error.message || 'Не удалось утвердить задания'}`);
    },
  });

  const handleSave = (vehicleId: number) => {
    saveMutation.mutate(vehicleId);
  };

  const handleApproveAll = () => {
    const savedCount = Array.from(vehicleTasks.values()).filter(t => t.isSaved).length;
    if (savedCount === 0) {
      alert('Нет сохраненных заданий для утверждения. Сначала сохраните задания.');
      return;
    }
    
    if (window.confirm(`Утвердить и отправить ${savedCount} задание(й) на борт техники?`)) {
      approveAllMutation.mutate();
    }
  };

  if (vehiclesLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-dark-bg">
        <Loader2 className="w-8 h-8 animate-spin text-primary-orange" />
        <span className="ml-3 text-gray-300">Загрузка...</span>
      </div>
    );
  }

  const savedTasksCount = Array.from(vehicleTasks.values()).filter(t => t.isSaved).length;

  // Подсчет общих значений для шапки
  const expandedVehiclesInfo = Array.from(vehicleTasks.entries())
    .filter(([_, task]) => task.isExpanded)
    .map(([vehicleId, task]) => {
      const vehicle = vehiclesData?.items.find(v => v.id === vehicleId);
      return {
        vehicle,
        plannedTotal: task.plannedTotal,
        distributedVolume: getDistributedVolume(task.routes),
        remainingVolume: getRemainingVolume(task.plannedTotal, task.routes),
      };
    });

  const totalPlanned = expandedVehiclesInfo.reduce((sum, info) => sum + info.plannedTotal, 0);
  const totalRemaining = expandedVehiclesInfo.reduce((sum, info) => sum + info.remainingVolume, 0);

  return (
    <div className="min-h-screen bg-dark-bg">
      {/* Sticky Header */}
      <div className="sticky top-0 z-50 bg-dark-card shadow-lg border-b-2 border-dark-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between gap-6">
            {/* Левая часть - Заголовок */}
            <div className="flex-shrink-0">
              <div className="space-y-2">
                <div className="flex gap-3">
                  <div>
                    <label className="block text-xs text-gray-500 uppercase mb-1">
                      Дата смены
                    </label>
                    <input
                      type="date"
                      value={selectedDate}
                      onChange={(e) => setSelectedDate(e.target.value)}
                      className="w-40 px-3 py-2 bg-dark-bg border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange focus:border-primary-orange text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 uppercase mb-1">
                      Смена <span className="text-primary-orange">*</span>
                    </label>
                    <select
                      value={globalWorkRegime || ''}
                      onChange={(e) => setGlobalWorkRegime(Number(e.target.value))}
                      className="w-52 px-3 py-2 bg-dark-bg border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange focus:border-primary-orange text-sm"
                    >
                      <option value="">Выберите смену</option>
                      {workRegimesData?.items.map((regime) => (
                        <option key={regime.id} value={regime.id}>
                          {regime.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                {savedTasksCount > 0 && (
                  <p className="text-sm text-primary-orange">
                    Сохранено заданий: {savedTasksCount}
                  </p>
                )}
              </div>
            </div>

            {/* Центральная часть - Информация по выбранной технике */}
            {expandedVehiclesInfo.length > 0 && (
              <div className="flex-1 bg-dark-bg rounded-lg p-4 border border-dark-border">
                <div className="flex flex-col items-center gap-4">
                  <div className="w-full text-center">
                    <div className="text-xs text-gray-500 uppercase mb-2">Выбранная техника</div>
                    <div className="flex flex-wrap gap-2 justify-center">
                      {expandedVehiclesInfo.map(({ vehicle }) => vehicle && (
                        <div key={vehicle.id} className="inline-flex items-center gap-2 bg-primary-orange/20 text-primary-orange px-3 py-1 rounded-lg text-sm font-medium">
                          <Truck className="w-4 h-4" />
                          {vehicle.name}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex gap-8 justify-center">
                    <div className="text-center">
                      <div className="text-xs text-gray-500 uppercase mb-1">Плановое значение</div>
                      <div className="text-2xl font-bold text-white">
                        {totalPlanned.toFixed(1)} <span className="text-sm text-gray-400">м³</span>
                      </div>
                    </div>

                    <div className="text-center">
                      <div className="text-xs text-gray-500 uppercase mb-1">Остаток</div>
                      <div className={`text-2xl font-bold ${
                        totalRemaining === 0 && totalPlanned > 0
                          ? 'text-primary-orange'
                          : 'text-white'
                      }`}>
                        {totalRemaining.toFixed(1)} <span className="text-sm text-gray-400">м³</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* Правая часть - Кнопка утверждения */}
            <div className="flex-shrink-0">
              <button
                onClick={handleApproveAll}
                disabled={approveAllMutation.isPending || savedTasksCount === 0}
                className="inline-flex items-center px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-dark-border disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors shadow-lg shadow-green-600/30"
              >
                {approveAllMutation.isPending ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Утверждение...
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5 mr-2" />
                    Утвердить ({savedTasksCount})
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Список техники с формами */}
        <div className="space-y-4">
          {vehiclesData?.items.map((vehicle) => {
            const taskState = vehicleTasks.get(vehicle.id);
            const isExpanded = taskState?.isExpanded || false;
            const vehicleCapacity = getVehicleCapacity(vehicle);
            const distributedVolume = taskState ? getDistributedVolume(taskState.routes) : 0;
            const remainingVolume = taskState ? getRemainingVolume(taskState.plannedTotal, taskState.routes) : 0;

            return (
              <div key={vehicle.id} className="bg-dark-card rounded-lg shadow-lg border border-dark-border">
                {/* Карточка техники */}
                <button
                  onClick={() => toggleVehicle(vehicle.id)}
                  className="w-full p-4 text-left hover:bg-dark-hover transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center gap-4 flex-1">
                    <Truck className="w-6 h-6 text-primary-orange" />
                    <div>
                      <h3 className="font-semibold text-white text-lg">{vehicle.name}</h3>
                      <p className="text-xs text-gray-500 uppercase">{vehicle.vehicle_type}</p>
                      {vehicle.model && (
                        <p className="text-xs text-gray-400 mt-0.5">{vehicle.model.name}</p>
                      )}
                    </div>
                    <div className="ml-auto mr-4 text-sm text-gray-400">
                      Вместительность: <span className="text-white font-medium">{vehicleCapacity} м³</span>
                    </div>
                    {taskState?.isSaved && (
                      <div className="flex items-center gap-2 bg-green-600/20 text-green-400 px-3 py-1 rounded-full text-sm">
                        <AlertCircle className="w-4 h-4" />
                        Сохранено
                      </div>
                    )}
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="w-5 h-5 text-gray-400" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                  )}
                </button>

                {/* Форма задания */}
                {isExpanded && taskState && (
                  <div className="border-t border-dark-border p-6">
                    {taskState.existingTaskId && (
                      <div className="mb-4 p-3 bg-primary-orange/10 border border-primary-orange/30 rounded-lg flex items-start gap-2">
                        <AlertCircle className="w-5 h-5 text-primary-orange flex-shrink-0 mt-0.5" />
                        <div className="text-sm text-gray-200">
                          <strong>Найдено существующее задание</strong> для этой техники на текущую смену. 
                          При сохранении оно будет обновлено.
                        </div>
                      </div>
                    )}

                    {/* Настройки задания */}
                    <div className="mb-6 pb-6 border-b border-dark-border">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                        {/* Колонка 1: Тип задания и Плановое значение */}
                        <div className="space-y-4">
                          {/* Тип задания */}
                          <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                              Тип задания <span className="text-primary-orange">*</span>
                            </label>
                            <select
                              value={taskState.taskType}
                              onChange={(e) => updateVehicleTask(vehicle.id, { taskType: e.target.value as TaskType })}
                              className="w-full px-3 py-2 bg-dark-bg border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange focus:border-primary-orange"
                            >
                              {Object.entries(TASK_TYPES).map(([key, label]) => (
                                <option key={key} value={key}>
                                  {label}
                                </option>
                              ))}
                            </select>
                          </div>

                          {/* Плановое значение */}
                          <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                              Плановое значение на смену (объем)
                            </label>
                            <input
                              type="number"
                              value={taskState.plannedTotal || ''}
                              onChange={(e) => updateVehicleTask(vehicle.id, { plannedTotal: e.target.value === '' ? 0 : Math.max(0, Number(e.target.value)) })}
                              className="w-full px-3 py-2 bg-dark-bg border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange focus:border-primary-orange"
                              placeholder="0"
                              min="0"
                            />
                          </div>
                        </div>

                        {/* Колонка 2: Режим ввода */}
                        <div>
                          <label className="block text-sm font-medium text-gray-300 mb-2">
                            Режим ввода
                          </label>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => updateVehicleTask(vehicle.id, { inputMode: 'volume' })}
                              className={`flex-1 px-3 py-2 rounded-lg border-2 transition-colors ${
                                taskState.inputMode === 'volume'
                                  ? 'border-primary-orange bg-primary-orange/20 text-primary-orange'
                                  : 'border-dark-border text-gray-400 hover:border-dark-hover'
                              }`}
                            >
                              <Weight className="w-4 h-4 mx-auto mb-1" />
                              <span className="text-xs">Объем</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => updateVehicleTask(vehicle.id, { inputMode: 'trips' })}
                              className={`flex-1 px-3 py-2 rounded-lg border-2 transition-colors ${
                                taskState.inputMode === 'trips'
                                  ? 'border-primary-orange bg-primary-orange/20 text-primary-orange'
                                  : 'border-dark-border text-gray-400 hover:border-dark-hover'
                              }`}
                            >
                              <Package2 className="w-4 h-4 mx-auto mb-1" />
                              <span className="text-xs">Рейсы</span>
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* Остаток - на всю ширину */}
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          Остаток (объем)
                        </label>
                        <div className={`px-3 py-2 border-2 rounded-lg font-semibold text-lg ${
                          remainingVolume === 0 && distributedVolume > 0
                            ? 'border-primary-orange bg-primary-orange/20 text-primary-orange'
                            : 'border-dark-border bg-dark-bg text-white'
                        }`}>
                          {remainingVolume.toFixed(1)} м³
                        </div>
                      </div>
                    </div>

                    {/* Маршруты */}
                    <div className="mb-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-white">Маршруты</h3>
                        <button
                          type="button"
                          onClick={() => addRoute(vehicle.id)}
                          className="inline-flex items-center px-3 py-2 bg-primary-orange hover:bg-secondary-orange text-white text-sm font-medium rounded-lg transition-colors shadow-md shadow-primary-orange/30"
                        >
                          <Plus className="w-4 h-4 mr-2" />
                          Добавить маршрут
                        </button>
                      </div>

                      {taskState.routes.length === 0 ? (
                        <div className="text-center py-12 bg-dark-bg rounded-lg border-2 border-dashed border-dark-border">
                          <p className="text-gray-400">Маршруты не добавлены</p>
                          <p className="text-sm text-gray-500 mt-1">Нажмите "Добавить маршрут" для начала</p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {taskState.routes.map((route, index) => (
                            <div
                              key={route.id}
                              className="p-4 bg-dark-bg rounded-lg border border-dark-border"
                            >
                              <div className="flex items-center justify-between mb-3">
                                <h4 className="font-medium text-white">Маршрут #{index + 1}</h4>
                                <button
                                  type="button"
                                  onClick={() => removeRoute(vehicle.id, route.id)}
                                  className="p-1 text-primary-orange hover:bg-primary-orange/20 rounded transition-colors"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>

                              <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
                                {/* Точка А */}
                                <div className="md:col-span-4">
                                  <label className="block text-xs font-medium text-gray-300 mb-1">
                                    Точка погрузки (А)
                                  </label>
                                  <select
                                    value={route.place_a_id || ''}
                                    onChange={(e) => updateRoute(vehicle.id, route.id, 'place_a_id', e.target.value)}
                                    className="w-full px-3 py-2 bg-dark-card border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange text-sm"
                                  >
                                    <option value="">Выберите точку</option>
                                    {loadingPlaces?.items.map((place) => (
                                      <option key={place.id} value={place.id}>
                                        {place.name}
                                      </option>
                                    ))}
                                  </select>
                                </div>

                                <div className="md:col-span-1 flex justify-center">
                                  <ArrowRight className="w-5 h-5 text-primary-orange" />
                                </div>

                                {/* Точка Б */}
                                <div className="md:col-span-4">
                                  <label className="block text-xs font-medium text-gray-300 mb-1">
                                    Точка разгрузки (Б)
                                  </label>
                                  <select
                                    value={route.place_b_id || ''}
                                    onChange={(e) => updateRoute(vehicle.id, route.id, 'place_b_id', e.target.value)}
                                    className="w-full px-3 py-2 bg-dark-card border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange text-sm"
                                  >
                                    <option value="">Выберите точку</option>
                                    {unloadingPlaces?.items.map((place) => (
                                      <option key={place.id} value={place.id}>
                                        {place.name}
                                      </option>
                                    ))}
                                  </select>
                                </div>

                                {/* Объем/Рейсы */}
                                <div className="md:col-span-3">
                                  {taskState.inputMode === 'volume' ? (
                                    <>
                                      <label className="block text-xs font-medium text-gray-300 mb-1">
                                        Объем
                                      </label>
                                      <input
                                        type="number"
                                        value={route.volume || ''}
                                        onChange={(e) => updateRoute(vehicle.id, route.id, 'volume', e.target.value === '' ? 0 : Number(e.target.value))}
                                        className="w-full px-3 py-2 bg-dark-card border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange text-sm"
                                        min="0"
                                        step="0.1"
                                      />
                                      <p className="text-xs text-gray-500 mt-1">
                                        ≈ {route.trips} рейс{route.trips !== 1 ? 'ов' : ''}
                                      </p>
                                    </>
                                  ) : (
                                    <>
                                      <label className="block text-xs font-medium text-gray-300 mb-1">
                                        Рейсов
                                      </label>
                                      <input
                                        type="number"
                                        value={route.trips || ''}
                                        onChange={(e) => updateRoute(vehicle.id, route.id, 'trips', e.target.value === '' ? 0 : Number(e.target.value))}
                                        className="w-full px-3 py-2 bg-dark-card border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange text-sm"
                                        min="0"
                                        step="1"
                                      />
                                      <p className="text-xs text-gray-500 mt-1">
                                        = {route.volume.toFixed(1)} м³
                                      </p>
                                    </>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Кнопка сохранения */}
                    <div className="flex justify-end pt-6 border-t border-dark-border">
                      <button
                        onClick={() => handleSave(vehicle.id)}
                        disabled={saveMutation.isPending || !globalWorkRegime || taskState.routes.length === 0}
                        className="inline-flex items-center px-6 py-3 bg-primary-orange hover:bg-secondary-orange disabled:bg-dark-border disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors shadow-lg shadow-primary-orange/30"
                      >
                        {saveMutation.isPending ? (
                          <>
                            <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                            Сохранение...
                          </>
                        ) : (
                          <>
                            <Save className="w-5 h-5 mr-2" />
                            Сохранить
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
