import { useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { useMutation, useQuery } from '@tanstack/react-query';
import { shiftTasksApi, vehiclesApi, workRegimesApi } from '../api/client';
import { ShiftTaskCreate } from '../types';
import { X, Plus, Trash2, Save, Loader2 } from 'lucide-react';

interface ShiftTaskFormProps {
  onClose: () => void;
  onSuccess: () => void;
}

export default function ShiftTaskForm({ onClose, onSuccess }: ShiftTaskFormProps) {
  const [error, setError] = useState<string | null>(null);

  const { data: vehicles } = useQuery({
    queryKey: ['vehicles'],
    queryFn: () => vehiclesApi.list({ enterprise_id: 1 }),
  });

  const { data: workRegimes } = useQuery({
    queryKey: ['work-regimes'],
    queryFn: () => workRegimesApi.list({ enterprise_id: 1 }),
  });

  const { register, control, handleSubmit, formState: { errors } } = useForm<ShiftTaskCreate>({
    defaultValues: {
      work_regime_id: 1,
      vehicle_id: 1,
      shift_date: new Date().toISOString().split('T')[0],
      task_name: '',
      priority: 0,
      status: 'pending',
      route_tasks: [],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'route_tasks',
  });

  const createMutation = useMutation({
    mutationFn: (data: ShiftTaskCreate) => shiftTasksApi.create(data),
    onSuccess: () => {
      onSuccess();
    },
    onError: (error: any) => {
      console.error('Failed to create task:', error);
      setError(error.response?.data?.detail || 'Не удалось создать задание');
    },
  });

  const onSubmit = (data: ShiftTaskCreate) => {
    setError(null);
    createMutation.mutate(data);
  };

  const addRoute = () => {
    append({
      route_order: fields.length + 1,
      planned_trips_count: 1,
      actual_trips_count: 0,
      status: 'pending',
      place_a_id: 0,
      place_b_id: 0,
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-card rounded-lg shadow-2xl border border-dark-border max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-dark-card border-b border-dark-border px-6 py-4 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white">Создать наряд-задание</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-dark-hover rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-gray-400" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6">
          {error && (
            <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-4">
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          {/* Basic Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Название задания
              </label>
              <input
                {...register('task_name')}
                type="text"
                className="w-full px-3 py-2 bg-dark-bg border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange focus:border-primary-orange"
                placeholder="Введите название"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Дата смены <span className="text-primary-orange">*</span>
              </label>
              <input
                {...register('shift_date', { required: 'Дата обязательна' })}
                type="date"
                className="w-full px-3 py-2 bg-dark-bg border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange focus:border-primary-orange"
              />
              {errors.shift_date && (
                <p className="mt-1 text-sm text-red-400">{errors.shift_date.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Техника <span className="text-primary-orange">*</span>
              </label>
              <select
                {...register('vehicle_id', { required: 'Техника обязательна', valueAsNumber: true })}
                className="w-full px-3 py-2 bg-dark-bg border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange focus:border-primary-orange"
              >
                <option value="">Выберите технику</option>
                {vehicles?.items?.map((vehicle) => (
                  <option key={vehicle.id} value={vehicle.id}>
                    {vehicle.name} ({vehicle.vehicle_type})
                  </option>
                ))}
              </select>
              {errors.vehicle_id && (
                <p className="mt-1 text-sm text-red-400">{errors.vehicle_id.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Режим работы <span className="text-primary-orange">*</span>
              </label>
              <select
                {...register('work_regime_id', { required: 'Режим работы обязателен', valueAsNumber: true })}
                className="w-full px-3 py-2 bg-dark-bg border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange focus:border-primary-orange"
              >
                <option value="">Выберите режим</option>
                {workRegimes?.items?.map((regime) => (
                  <option key={regime.id} value={regime.id}>
                    {regime.name}
                  </option>
                ))}
              </select>
              {errors.work_regime_id && (
                <p className="mt-1 text-sm text-red-400">{errors.work_regime_id.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Приоритет
              </label>
              <input
                {...register('priority', { valueAsNumber: true })}
                type="number"
                min="0"
                className="w-full px-3 py-2 bg-dark-bg border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange focus:border-primary-orange"
                placeholder="0"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Статус
              </label>
              <select
                {...register('status')}
                className="w-full px-3 py-2 bg-dark-bg border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange focus:border-primary-orange"
              >
                <option value="pending">Ожидает</option>
                <option value="in_progress">В работе</option>
                <option value="completed">Завершено</option>
                <option value="cancelled">Отменено</option>
              </select>
            </div>
          </div>

          {/* Routes Section */}
          <div className="border-t border-dark-border pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Маршруты</h3>
              <button
                type="button"
                onClick={addRoute}
                className="inline-flex items-center px-3 py-2 bg-primary-orange hover:bg-secondary-orange text-white text-sm font-medium rounded-lg transition-colors shadow-md shadow-primary-orange/30"
              >
                <Plus className="w-4 h-4 mr-2" />
                Добавить маршрут
              </button>
            </div>

            {fields.length === 0 && (
              <div className="text-center py-8 bg-dark-bg rounded-lg border border-dark-border">
                <p className="text-gray-400">Маршруты не добавлены</p>
              </div>
            )}

            <div className="space-y-4">
              {fields.map((field, index) => (
                <div key={field.id} className="bg-dark-bg rounded-lg p-4 border border-dark-border">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="font-medium text-white">Маршрут #{index + 1}</h4>
                    <button
                      type="button"
                      onClick={() => remove(index)}
                      className="p-1 text-primary-orange hover:bg-primary-orange/20 rounded transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">
                        Порядок
                      </label>
                      <input
                        {...register(`route_tasks.${index}.route_order`, { valueAsNumber: true })}
                        type="number"
                        min="1"
                        className="w-full px-3 py-2 bg-dark-card border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">
                        Точка А <span className="text-primary-orange">*</span>
                      </label>
                      <input
                        {...register(`route_tasks.${index}.place_a_id`, {
                          required: true,
                        })}
                        type="number"
                        min="1"
                        className="w-full px-3 py-2 bg-dark-card border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">
                        Точка Б <span className="text-primary-orange">*</span>
                      </label>
                      <input
                        {...register(`route_tasks.${index}.place_b_id`, {
                          required: true,
                        })}
                        type="number"
                        min="1"
                        className="w-full px-3 py-2 bg-dark-card border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">
                        Рейсов
                      </label>
                      <input
                        {...register(`route_tasks.${index}.planned_trips_count`, { valueAsNumber: true })}
                        type="number"
                        min="1"
                        className="w-full px-3 py-2 bg-dark-card border border-dark-border text-white rounded-lg focus:ring-2 focus:ring-primary-orange"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-6 border-t border-dark-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-300 hover:bg-dark-hover font-medium rounded-lg transition-colors"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="inline-flex items-center px-4 py-2 bg-primary-orange hover:bg-secondary-orange text-white font-medium rounded-lg transition-colors shadow-lg shadow-primary-orange/30 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Создание...
                </>
              ) : (
                <>
                  <Save className="w-5 h-5 mr-2" />
                  Создать задание
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

