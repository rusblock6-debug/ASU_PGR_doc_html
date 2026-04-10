/**
 * Тестовое окно для импорта JSON задач
 * ЛЕГКО УДАЛЯЕТСЯ - просто закомментировать импорт и роут
 */
import { useState } from 'react';
import { tripServiceApi, CreateShiftTaskPayload } from '@/shared/api/tripServiceApi';
import './TestDataImportModal.css';


type ImportData = CreateShiftTaskPayload;

interface TestDataImportModalProps {
  onImportSuccess?: () => void;
}

export const TestDataImportModal = ({ onImportSuccess }: TestDataImportModalProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [jsonText, setJsonText] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
//TODO заменить на более реалистичные данные, возможно убрать weight: , volume: ,
  // Пример JSON для быстрого тестирования
  const exampleJson: ImportData = {
    id: 'shift-2025-11-12',
    work_regime_id: 1,
    vehicle_id: 1001,
    shift_date: '2025-11-12',
    task_name: 'Дневная смена',
    priority: 1,
    status: 'pending',
    task_data: {
      dispatcher: 'Иван Иванов',
      notes: 'Сменное задание от 12 ноября',
    },
    route_tasks: [
      {
        id: 'route-001',
        route_order: 1,
        place_a_id: 3,
        place_b_id: 5,
        planned_trips_count: 4,
        actual_trips_count: 0,
        status: 'pending',
        route_data: {
          weight: 25,
          volume: 15,
          message_to_driver: 'Погрузка песка с соблюдением техники безопасности',
        },
      },
      {
        id: 'route-002',
        route_order: 2,
        place_a_id: 5,
        place_b_id: 3,
        planned_trips_count: 3,
        actual_trips_count: 0,
        status: 'pending',
        route_data: {
          weight: 22,
          volume: 12,
          message_to_driver: 'Доставка грунта на свалку',
        },
      },
    ],
  };

  const handleLoadExample = () => {
    setJsonText(JSON.stringify(exampleJson, null, 2));
  };

  const handleImport = async () => {
    setLoading(true);
    setMessage(null);

    try {
      // Парсим JSON
      const data: ImportData = JSON.parse(jsonText);

      if (!data?.id) {
        throw new Error('Поле "id" (shift_id) обязательно');
      }
      if (!data.work_regime_id) {
        throw new Error('Поле "work_regime_id" обязательно');
      }
      if (!data.vehicle_id) {
        throw new Error('Поле "vehicle_id" обязательно');
      }
      if (!data.shift_date) {
        throw new Error('Поле "shift_date" обязательно');
      }
      if (!data.task_name) {
        throw new Error('Поле "task_name" обязательно');
      }
      if (!data.route_tasks || data.route_tasks.length === 0) {
        throw new Error('Необходимо указать как минимум один маршрут в "route_tasks"');
      }

      const payload: CreateShiftTaskPayload = {
        id: data.id,
        work_regime_id: Number(data.work_regime_id),
        vehicle_id: Number(data.vehicle_id),
        shift_date: data.shift_date,
        task_name: data.task_name,
        priority: data.priority ?? 0,
        status: data.status ?? 'pending',
        sent_to_board_at: data.sent_to_board_at,
        acknowledged_at: data.acknowledged_at,
        started_at: data.started_at,
        completed_at: data.completed_at,
        task_data: data.task_data,
        route_tasks: data.route_tasks.map((route, index) => {
          // Проверяем place_a_id и place_b_id
          const placeAId = route.place_a_id !== null && route.place_a_id !== undefined 
            ? Number(route.place_a_id) 
            : null;
          const placeBId = route.place_b_id !== null && route.place_b_id !== undefined 
            ? Number(route.place_b_id) 
            : null;

          if (placeAId === null || placeBId === null) {
            throw new Error(
              `Маршрут ${route.id || index + 1}: поля "place_a_id" и "place_b_id" обязательны и не могут быть null`
            );
          }

          return {
            id: route.id,
            route_order: route.route_order ?? index + 1,
            place_a_id: placeAId,
            place_b_id: placeBId,
            planned_trips_count: route.planned_trips_count ?? 1,
            actual_trips_count: route.actual_trips_count ?? 0,
            status: route.status ?? 'pending',
            route_data: route.route_data,
          };
        }),
      };

      console.log('📤 Создаем сменное задание:', payload);

      await tripServiceApi.createShiftTask(payload);

      setMessage({
        type: 'success',
        text: `✅ Смена ${payload.id} успешно создана (${payload.route_tasks.length} маршрутов)`,
      });

      // Обновить данные на странице
      if (onImportSuccess) {
        onImportSuccess();
      }

      // Очистить форму
      setJsonText('');

      // Закрыть через 2 секунды
      setTimeout(() => setIsOpen(false), 2000);
    } catch (err: any) {
      console.error('❌ Ошибка импорта:', err);
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'Неизвестная ошибка';
      setMessage({
        type: 'error',
        text: `❌ Ошибка: ${detail}`,
      });
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) {
    return (
      <button 
        className="test-import-button"
        onClick={() => setIsOpen(true)}
        title="Добавление задания"
      >
        ➕ Добавление задания
      </button>
    );
  }

  return (
    <div className="test-import-modal-overlay">
      <div className="test-import-modal">
        <div className="modal-header">
          <h2>➕ Добавление задания</h2>
          <button 
            className="close-button"
            onClick={() => setIsOpen(false)}
          >
            ✕
          </button>
        </div>

        <div className="modal-content">
          <div className="description">
            <p>Вставьте JSON с данными смены:</p>
            <code>
{`{
  "id": "shift-2025-11-12",
  "work_regime_id": 1,
  "vehicle_id": 1001,
  "shift_date": "2025-11-12",
  "task_name": "Дневная смена",
  "priority": 1,
  "status": "pending",
  "task_data": {},
  "route_tasks": [
    {
      "id": "route-001",
      "route_order": 1,
      "place_a_id": 3,
      "place_b_id": 5,
      "planned_trips_count": 4,
      "status": "pending",
      "route_data": {
        "message_to_driver": "Текст сообщения"
      }
    }
  ]
}`}
            </code>
          </div>

          <textarea
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            placeholder="Вставьте JSON здесь..."
            className="json-textarea"
          />

          {message && (
            <div className={`message ${message.type}`}>
              {message.text}
            </div>
          )}

          <div className="modal-actions">
            <button
              className="btn-secondary"
              onClick={handleLoadExample}
              disabled={loading}
            >
              📋 Пример
            </button>
            <button
              className="btn-primary"
              onClick={handleImport}
              disabled={loading || !jsonText.trim()}
            >
              {loading ? 'Загрузка...' : '✅ Импортировать'}
            </button>
            <button
              className="btn-secondary"
              onClick={() => setIsOpen(false)}
              disabled={loading}
            >
              Закрыть
            </button>
          </div>
        </div>

        <div className="modal-info">
          <small>💡 Это тестовое окно - легко удаляется (см. комментарии в коде)</small>
        </div>
      </div>
    </div>
  );
};
