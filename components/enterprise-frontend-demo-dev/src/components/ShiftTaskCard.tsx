import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { shiftTasksApi } from '../api/client';
import { ShiftTask } from '../types';
import { Trash2, Calendar, Truck, AlertCircle, CheckCircle2, Clock, MapPin } from 'lucide-react';
import { format } from 'date-fns';

interface ShiftTaskCardProps {
  task: ShiftTask;
  onUpdate: () => void;
}

const statusColors: Record<string, { bg: string; text: string; icon: any }> = {
  pending: { bg: 'bg-dark-bg', text: 'text-gray-400', icon: Clock },
  in_progress: { bg: 'bg-primary-orange/20', text: 'text-primary-orange', icon: Clock },
  completed: { bg: 'bg-green-900/30', text: 'text-green-400', icon: CheckCircle2 },
  cancelled: { bg: 'bg-red-900/30', text: 'text-red-400', icon: AlertCircle },
};

const statusLabels: Record<string, string> = {
  pending: 'Ожидает',
  in_progress: 'В работе',
  completed: 'Завершено',
  cancelled: 'Отменено',
};

export default function ShiftTaskCard({ task, onUpdate }: ShiftTaskCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => shiftTasksApi.delete(task.id),
    onSuccess: () => {
      onUpdate();
    },
    onError: (error) => {
      console.error('Failed to delete task:', error);
      alert('Не удалось удалить задание');
      setIsDeleting(false);
    },
  });

  const handleDelete = () => {
    if (window.confirm('Вы уверены, что хотите удалить это задание?')) {
      setIsDeleting(true);
      deleteMutation.mutate();
    }
  };

  const statusConfig = statusColors[task.status] || statusColors.pending;
  const StatusIcon = statusConfig.icon;

  return (
    <div className="bg-dark-card rounded-lg shadow-lg border border-dark-border hover:shadow-xl hover:shadow-primary-orange/10 transition-shadow">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-lg font-semibold text-white">
                {task.task_name || `Задание #${task.id.substring(0, 8)}`}
              </h3>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.text}`}>
                <StatusIcon className="w-3 h-3 mr-1" />
                {statusLabels[task.status] || task.status}
              </span>
            </div>
            <p className="text-sm text-gray-500 font-mono">ID: {task.id}</p>
          </div>
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="p-2 text-primary-orange hover:bg-primary-orange/20 rounded-lg transition-colors disabled:opacity-50"
            title="Удалить задание"
          >
            <Trash2 className="w-5 h-5" />
          </button>
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="flex items-center text-sm">
            <Calendar className="w-4 h-4 text-primary-orange mr-2" />
            <span className="text-gray-400">Дата:</span>
            <span className="ml-2 font-medium text-white">
              {task.shift_date}
            </span>
          </div>
          <div className="flex items-center text-sm">
            <Truck className="w-4 h-4 text-primary-orange mr-2" />
            <span className="text-gray-400">Техника ID:</span>
            <span className="ml-2 font-medium text-white">{task.vehicle_id}</span>
          </div>
          <div className="flex items-center text-sm">
            <span className="text-gray-400">Приоритет:</span>
            <span className="ml-2 font-medium text-white">{task.priority}</span>
          </div>
        </div>

        {/* Route Tasks */}
        {task.route_tasks && task.route_tasks.length > 0 && (
          <div className="mt-4 pt-4 border-t border-dark-border">
            <h4 className="text-sm font-medium text-gray-300 mb-3 flex items-center">
              <MapPin className="w-4 h-4 mr-2 text-primary-orange" />
              Маршруты ({task.route_tasks.length})
            </h4>
            <div className="space-y-2">
              {task.route_tasks.map((route, idx) => (
                <div key={route.id || idx} className="bg-dark-bg rounded-lg p-3 border border-dark-border">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 text-sm">
                      <span className="font-medium text-white">
                        Маршрут #{route.route_order}
                      </span>
                      <span className="text-gray-400">
                        Место погрузки: <span className="font-medium text-white">{route.place_a_id}</span>
                      </span>
                      <span className="text-gray-400">
                        Место разгрузки: <span className="font-medium text-white">{route.place_b_id}</span>
                      </span>
                    </div>
                    <div className="text-sm">
                      <span className="text-gray-400">Рейсов:</span>
                      <span className="ml-2 font-medium text-primary-orange">
                        {route.actual_trips_count || 0} / {route.planned_trips_count}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Timestamps */}
        {task.created_at && (
          <div className="mt-4 pt-4 border-t border-dark-border">
            <p className="text-xs text-gray-500">
              Создано: {format(new Date(task.created_at), 'dd.MM.yyyy, HH:mm')}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

