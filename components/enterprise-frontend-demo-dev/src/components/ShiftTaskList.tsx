import { useQuery } from '@tanstack/react-query';
import { shiftTasksApi } from '../api/client';
import ShiftTaskCard from './ShiftTaskCard';
import { Loader2, AlertCircle } from 'lucide-react';

interface ShiftTaskListProps {
  vehicleId?: number;
  shiftDate?: string;
}

export default function ShiftTaskList({ vehicleId, shiftDate }: ShiftTaskListProps) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['shift-tasks', vehicleId, shiftDate],
    queryFn: () => shiftTasksApi.list({
      enterprise_id: 1,
      vehicle_id: vehicleId,
      shift_date: shiftDate,
      page: 1,
      size: 50,
    }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary-orange" />
        <span className="ml-3 text-gray-300">Загрузка заданий...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-6">
        <div className="flex items-center">
          <AlertCircle className="w-6 h-6 text-red-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-300">Ошибка загрузки</h3>
            <p className="text-sm text-red-400 mt-1">
              {error instanceof Error ? error.message : 'Не удалось загрузить задания'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="bg-dark-card rounded-lg shadow-lg border border-dark-border p-12 text-center">
        <div className="text-gray-500 mb-4">
          <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-white mb-2">Нет заданий</h3>
        <p className="text-gray-400">
          Создайте первое наряд-задание для начала работы
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-400">
          Найдено заданий: <span className="font-semibold text-primary-orange">{data.total}</span>
        </p>
        <button
          onClick={() => refetch()}
          className="text-sm text-primary-orange hover:text-secondary-orange font-medium"
        >
          Обновить
        </button>
      </div>

      <div className="space-y-4">
        {data.items.map((task) => (
          <ShiftTaskCard key={task.id} task={task} onUpdate={() => refetch()} />
        ))}
      </div>
    </div>
  );
}

