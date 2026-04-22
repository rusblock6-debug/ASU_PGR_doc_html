import { useState, useEffect } from 'react';
import { tripServiceApi } from '@/shared/api/tripServiceApi';
import './ManualActionsPage.css';

type StateType = 
  | 'idle' 
  | 'moving_empty' 
  | 'stopped_empty' 
  | 'loading' 
  | 'moving_loaded' 
  | 'stopped_loaded' 
  | 'unloading';

interface StateInfo {
  label: string;
  icon: string;
  isMoving: boolean;
}

// Описание состояний
const STATE_INFO: Record<StateType, StateInfo> = {
  idle: { label: 'Ожидание задания', icon: '⏸️', isMoving: false },
  moving_empty: { label: 'Движение порожним', icon: '🚚', isMoving: true },
  stopped_empty: { label: 'Остановка порожним', icon: '🅿️', isMoving: false },
  loading: { label: 'Погрузка', icon: '📦', isMoving: false },
  moving_loaded: { label: 'Движение с грузом', icon: '🚛', isMoving: true },
  stopped_loaded: { label: 'Остановка с грузом', icon: '🛑', isMoving: false },
  unloading: { label: 'Разгрузка', icon: '📤', isMoving: false },
};

// Определение следующего состояния для каждого текущего состояния
const NEXT_STATE: Record<StateType, StateType | null> = {
  idle: null, // Определяется динамически на основе previous_state
  moving_empty: 'stopped_empty',
  stopped_empty: 'loading',
  loading: 'moving_loaded',
  moving_loaded: 'stopped_loaded',
  stopped_loaded: 'unloading',
  unloading: 'moving_empty',
};

// Функция для определения следующего состояния после выхода из idle
function getNextStateAfterIdle(previousState: StateType | null): StateType {
  if (!previousState) {
    return 'moving_empty'; // По умолчанию начинаем с движения порожним
  }
  
  // ВАЖНО: Если перешли в idle из состояния ДВИЖЕНИЯ (moving_*),
  // то следующее состояние - это ТО ЖЕ движение (продолжаем ехать)
  if (previousState === 'moving_empty') {
    return 'moving_empty'; // Продолжаем движение порожним
  }
  if (previousState === 'moving_loaded') {
    return 'moving_loaded'; // Продолжаем движение с грузом
  }
  
  // Для всех остальных состояний возвращаем следующее по циклу
  const nextState = NEXT_STATE[previousState];
  return nextState || 'moving_empty';
}

export const ManualActionsPage = () => {
  const [currentState, setCurrentState] = useState<StateType | ''>('');
  const [previousState, setPreviousState] = useState<StateType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadCurrentState = async () => {
    try {
      const state = await tripServiceApi.getCurrentState();
      setCurrentState(state.state as StateType);
      setPreviousState((state.previous_state as StateType) || null);
    } catch (err: any) {
      console.error('Failed to load current state:', err);
      setError('Ошибка загрузки текущего состояния');
    }
  };

  useEffect(() => {
    loadCurrentState();
    // Обновляем состояние каждые 3 секунды
    const interval = setInterval(loadCurrentState, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleTransition = async (newState: StateType, actionLabel: string) => {
    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await tripServiceApi.transitionState({
        new_state: newState,
        reason: 'manual_action',
        comment: `Ручное действие: ${actionLabel}`,
      });

      setSuccessMessage(`Успешно выполнено: ${actionLabel}`);
      await loadCurrentState();

      // Очистить сообщение через 3 секунды
      setTimeout(() => {
        setSuccessMessage(null);
      }, 3000);
    } catch (err: any) {
      console.error('Failed to perform action:', err);
      setError(err.response?.data?.detail || 'Ошибка выполнения действия');
    } finally {
      setLoading(false);
    }
  };

  const currentStateInfo = currentState ? STATE_INFO[currentState] : null;
  
  // Определяем следующее состояние
  let nextState: StateType | null = null;
  if (currentState === 'idle') {
    // Если в idle, следующее состояние зависит от previous_state
    nextState = getNextStateAfterIdle(previousState);
  } else if (currentState) {
    // Иначе берем из таблицы переходов
    nextState = NEXT_STATE[currentState as StateType];
  }

  return (
    <div className="manual-actions-page">
      <h1>Ручные действия</h1>
      <p className="subtitle">Управление состояниями рейса</p>

      {!currentState ? (
        <div className="loading-state">Загрузка текущего состояния...</div>
      ) : (
        <div className="state-control">
          {/* Левая кнопка - текущее состояние / переход в Простой */}
          <button
            className={`state-button current-state ${currentState === 'idle' ? 'idle' : ''}`}
            onClick={() => {
              if (currentState !== 'idle') {
                handleTransition('idle', 'Простой');
              }
            }}
            disabled={loading || currentState === 'idle'}
          >
            <div className="state-icon">{currentStateInfo?.icon}</div>
            <div className="state-content">
              <div className="state-label">Текущее состояние</div>
              <div className="state-value">{currentStateInfo?.label}</div>
              {currentState !== 'idle' && <div className="state-hint">Нажмите для перехода в Простой</div>}
            </div>
          </button>

          {/* Стрелка */}
          <div className="state-arrow">→</div>

          {/* Правая кнопка - следующее состояние */}
          {nextState ? (
            <button
              className="state-button next-state"
              onClick={() => {
                handleTransition(nextState, STATE_INFO[nextState].label);
              }}
              disabled={loading}
            >
              <div className="state-icon">{STATE_INFO[nextState].icon}</div>
              <div className="state-content">
                <div className="state-label">Следующее состояние</div>
                <div className="state-value">{STATE_INFO[nextState].label}</div>
                <div className="state-hint">Нажмите для перехода</div>
              </div>
            </button>
          ) : (
            <div className="state-button next-state disabled">
              <div className="state-content">
                <div className="state-label">Следующее состояние</div>
                <div className="state-value">—</div>
              </div>
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="error-message">
          <span className="error-icon">⚠️</span>
          {error}
        </div>
      )}

      {successMessage && (
        <div className="success-message">
          <span className="success-icon">✅</span>
          {successMessage}
        </div>
      )}

      <div className="info-card">
        <h3>ℹ️ Как работает</h3>
        <ul>
          <li><strong>Левая кнопка</strong> — показывает текущее состояние. Нажмите для перехода в <strong>Простой (idle)</strong>.</li>
          <li><strong>Правая кнопка</strong> — переход к следующему состоянию в цикле рейса.</li>
          <li>При выходе из Простоя система продолжит с того места, где остановились.</li>
          <li>Состояние обновляется автоматически каждые 3 секунды.</li>
          <li>Переходы выполняются немедленно и могут создавать или завершать рейсы.</li>
        </ul>
      </div>
    </div>
  );
};




