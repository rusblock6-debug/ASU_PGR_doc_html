/**
 * Компонент левой панели инструментов редактора графа
 */
import React, { useState, useEffect } from 'react';
import { Horizon } from '../../types/graph';

type EditorMode = 'view' | 'addNode' | 'addEdge' | 'addPlace' | 'addLadder' | 'move' | 'edit' | 'delete';

interface EditorToolbarProps {
  isOpen: boolean;
  activeTab: 'horizons' | 'tools';
  horizons: Horizon[];
  selectedHorizon: Horizon | null;
  onHorizonChange: (level: Horizon | null) => void;
  onCreateHorizon: (name: string, height: number, color?: string) => Promise<void>;
  onDeleteHorizon: (levelId: number) => Promise<void>;
  onImportGraph: () => void;
  mode: EditorMode;
  onModeChange: (mode: EditorMode) => void;
  scale: number;
  offset: { x: number; y: number };
  onZoom: (delta: number) => void;
  onResetView: () => void;
  cursorPos: { x: number; y: number } | null;
  onClosePanel?: () => void;
}

export function EditorToolbar({
  isOpen,
  activeTab,
  horizons: levels = [],
  selectedHorizon,
  onHorizonChange,
  onCreateHorizon,
  onDeleteHorizon,
  onImportGraph,
  mode,
  onModeChange,
  scale,
  offset,
  onZoom,
  onResetView,
  cursorPos,
  onClosePanel,
}: EditorToolbarProps) {
  // Гарантируем, что levels всегда массив
  // Проверяем разные возможные форматы данных
  let safeLevels: Horizon[] = [];
  
  try {
    if (levels === null || levels === undefined) {
      safeLevels = [];
    } else if (Array.isArray(levels)) {
      safeLevels = levels;
    } else if (typeof levels === 'object' && levels !== null) {
      // Проверяем, является ли это объектом пагинации
      if ('items' in levels && Array.isArray((levels as any).items)) {
        safeLevels = (levels as any).items;
      } else {
        // Если это не массив и не объект пагинации, пробуем преобразовать
        console.warn('EditorToolbar: unexpected levels format, converting to array:', levels);
        safeLevels = [];
      }
    } else {
      safeLevels = [];
    }
  } catch (error) {
    console.error('EditorToolbar: error processing levels:', error, levels);
    safeLevels = [];
  }

  if (!Array.isArray(safeLevels)) {
    console.error('EditorToolbar: safeLevels is not an array after processing!', safeLevels);
    safeLevels = [];
  }
  
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newHorizonName, setNewHorizonName] = useState('');
  // Предзаполняем высоту на основе текущего горизонта
  const [newHorizonHeight, setNewHorizonHeight] = useState(() => {
    if (selectedHorizon) {
      // Предлагаем высоту на 50м выше текущего горизонта
      return selectedHorizon.height + 50;
    }
    return 0;
  });
  const [newHorizonColor, setNewHorizonColor] = useState('#2196F3');  // Дефолтный синий цвет
  const [isCreating, setIsCreating] = useState(false);

  // Обновляем предзаполнение при изменении выбранного горизонта
  useEffect(() => {
    if (selectedHorizon && !showCreateForm) {
      setNewHorizonHeight(selectedHorizon.height + 50);
    }
  }, [selectedHorizon, showCreateForm]);

  useEffect(() => {
    if (activeTab !== 'horizons' && showCreateForm) {
      setShowCreateForm(false);
    }
  }, [activeTab, showCreateForm]);

  const handleCreateHorizon = async () => {
    if (!newHorizonName.trim()) {
      alert('Введите название горизонта');
      return;
    }

    setIsCreating(true);
    try {
      await onCreateHorizon(newHorizonName, newHorizonHeight, newHorizonColor);
      setNewHorizonName('');
      setNewHorizonHeight(0);
      setNewHorizonColor('#2196F3');  // Сброс на дефолтный цвет
      setShowCreateForm(false);
    } catch (error) {
      console.error('Error creating level:', error);
      alert('Ошибка при создании горизонта');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteHorizon = async () => {
    if (!selectedHorizon) return;

    if (window.confirm(`Вы уверены, что хотите удалить горизонт "${selectedHorizon.name}"?\n\nЭто действие необратимо!`)) {
      try {
        await onDeleteHorizon(selectedHorizon.id);
      } catch (error) {
        console.error('Error deleting level:', error);
        alert('Ошибка при удалении горизонта');
      }
    }
  };

  if (!isOpen) {
    return null;
  }

  const renderHorizonSection = () => (
    <div className="level-selector">
      <div className="panel-section-header">
        <label>Горизонты</label>
        {onClosePanel && (
          <button
            type="button"
            className="panel-toggle-inline"
            onClick={onClosePanel}
            title="Скрыть панель"
          >
            <span aria-hidden="true">—</span>
            <span className="sr-only">Скрыть панель</span>
          </button>
        )}
      </div>
      <div className="level-selector-content">
        <select
          className="level-selector-control"
          value={selectedHorizon?.id || ''}
          onChange={(e) => {
            const level = safeLevels.find(l => l.id === parseInt(e.target.value)) || null;
            onHorizonChange(level);
          }}
        >
          {safeLevels.length === 0 ? (
            <option disabled>Загрузка горизонтов...</option>
          ) : (
            safeLevels.map(level => (
              <option key={level.id} value={level.id}>
                {level.name} (h: {level.height})
              </option>
            ))
          )}
        </select>

        <div className="level-action-grid">
          <button
            className="level-action"
            onClick={() => setShowCreateForm(prev => !prev)}
          >
            {showCreateForm ? 'Отменить' : '+ Новый горизонт'}
          </button>
          <button
            className="level-action"
            onClick={onImportGraph}
            title="Импортировать граф из внешнего источника"
          >
            📥 Импорт
          </button>
          {selectedHorizon && (
            <button
              className="level-action danger"
              onClick={handleDeleteHorizon}
              title="Удалить текущий горизонт"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style={{ display: 'block' }}>
                <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z" />
                <path fillRule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z" />
              </svg>
            </button>
          )}
        </div>

        {selectedHorizon && !showCreateForm && (
          <div className="level-editor-card">
            <div className="field-group">
              <label>Название горизонта:</label>
              <input
                type="text"
                value={selectedHorizon.name}
                onChange={async (e) => {
                  const newName = e.target.value;
                  if (!newName.trim()) return;

                  try {
                    const response = await fetch(`/api/horizons/${selectedHorizon.id}`, {
                      method: 'PATCH',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ name: newName })
                    });
                    if (!response.ok) throw new Error('Failed to update name');

                    const updatedHorizon = { ...selectedHorizon, name: newName };
                    onHorizonChange(updatedHorizon);
                  } catch (error) {
                    console.error('Error updating level name:', error);
                    alert('Ошибка при обновлении названия горизонта');
                  }
                }}
                placeholder="Название горизонта"
              />
            </div>
            <div className="field-group">
              <label>Цвет горизонта:</label>
              <div className="color-row">
                <input
                  type="color"
                  value={selectedHorizon.color || '#2196F3'}
                  onChange={async (e) => {
                    const newColor = e.target.value;
                    try {
                      const response = await fetch(`/api/horizons/${selectedHorizon.id}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ color: newColor })
                      });
                      if (!response.ok) throw new Error('Failed to update color');

                      const updatedHorizon = { ...selectedHorizon, color: newColor };
                      onHorizonChange(updatedHorizon);
                    } catch (error) {
                      console.error('Error updating level color:', error);
                      alert('Ошибка при обновлении цвета горизонта');
                    }
                  }}
                />
                <input
                  type="text"
                  value={selectedHorizon.color || '#2196F3'}
                  onChange={async (e) => {
                    const newColor = e.target.value;
                    if (!/^#[0-9A-Fa-f]{6}$/.test(newColor)) return;

                    try {
                      const response = await fetch(`/api/horizons/${selectedHorizon.id}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ color: newColor })
                      });
                      if (!response.ok) throw new Error('Failed to update color');

                      const updatedHorizon = { ...selectedHorizon, color: newColor };
                      onHorizonChange(updatedHorizon);
                    } catch (error) {
                      console.error('Error updating level color:', error);
                    }
                  }}
                  placeholder="#2196F3"
                  pattern="^#[0-9A-Fa-f]{6}$"
                />
              </div>
              <small>Рёбра этого горизонта окрашены в этот цвет</small>
            </div>
            <div className="field-group">
              <label>Высота горизонта (м):</label>
              <input
                type="number"
                value={selectedHorizon.height}
                onChange={async (e) => {
                  const newHeight = parseFloat(e.target.value);
                  if (isNaN(newHeight)) return;

                  try {
                    const response = await fetch(`/api/horizons/${selectedHorizon.id}`, {
                      method: 'PATCH',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ height: newHeight })
                    });
                    if (!response.ok) throw new Error('Failed to update height');

                    const updatedHorizon = { ...selectedHorizon, height: newHeight };
                    onHorizonChange(updatedHorizon);
                  } catch (error) {
                    console.error('Error updating level height:', error);
                    alert('Ошибка при обновлении высоты горизонта');
                  }
                }}
                step="10"
                placeholder="0"
              />
              <small>Высота горизонта в метрах (можно использовать 0)</small>
            </div>
          </div>
        )}

        {showCreateForm && (
          <div className="level-create-card">
            <div className="field-group">
              <label>Название:</label>
              <input
                type="text"
                value={newHorizonName}
                onChange={(e) => setNewHorizonName(e.target.value)}
                placeholder="Горизонт -50"
                disabled={isCreating}
              />
            </div>
            <div className="field-group">
              <label>Высота (м):</label>
              <div className="numeric-control">
                <input
                  type="number"
                  value={newHorizonHeight}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value);
                    setNewHorizonHeight(isNaN(val) ? 0 : val);
                  }}
                  placeholder="0"
                  step="10"
                  disabled={isCreating}
                />
                <div className="numeric-buttons">
                  <button
                    type="button"
                    onClick={() => setNewHorizonHeight(prev => prev + 10)}
                    disabled={isCreating}
                    title="Увеличить на 10м"
                  >
                    ▲
                  </button>
                  <button
                    type="button"
                    onClick={() => setNewHorizonHeight(prev => prev - 10)}
                    disabled={isCreating}
                    title="Уменьшить на 10м"
                  >
                    ▼
                  </button>
                </div>
              </div>
              <small>Текущий горизонт: {selectedHorizon?.height || 0}м</small>
            </div>
            <div className="field-group">
              <label>Цвет (для визуализации в 3D):</label>
              <div className="color-row">
                <input
                  type="color"
                  value={newHorizonColor}
                  onChange={(e) => setNewHorizonColor(e.target.value)}
                  disabled={isCreating}
                />
                <input
                  type="text"
                  value={newHorizonColor}
                  onChange={(e) => setNewHorizonColor(e.target.value)}
                  placeholder="#2196F3"
                  disabled={isCreating}
                  pattern="^#[0-9A-Fa-f]{6}$"
                />
              </div>
              <small>Рёбра этого горизонта будут окрашены в выбранный цвет</small>
            </div>
            <button
              className="level-action primary create"
              onClick={handleCreateHorizon}
              disabled={isCreating}
            >
              {isCreating ? 'Создание...' : 'Создать'}
            </button>
          </div>
        )}
      </div>
    </div>
  );

  const renderToolSection = () => (
    <div className="toolbar">
      <div className="toolbar-header">
        <label>Инструменты</label>
        {onClosePanel && (
          <button
            type="button"
            className="panel-toggle-inline"
            onClick={onClosePanel}
            title="Скрыть панель"
          >
            <span aria-hidden="true">—</span>
            <span className="sr-only">Скрыть панель</span>
          </button>
        )}
      </div>
      <div className="toolbar-buttons">
        <button
          className={`tool-button ${mode === 'view' ? 'active' : ''}`}
          onClick={() => onModeChange('view')}
          title="Просмотр и выбор (V)"
        >
          <span className="tool-icon">👆</span>
          <span className="tool-label">Выбор</span>
        </button>
        <button
          className={`tool-button ${mode === 'addNode' ? 'active' : ''}`}
          onClick={() => onModeChange('addNode')}
          title="Добавить узел дороги (N)"
        >
          <span className="tool-icon">⬤</span>
          <span className="tool-label">Узел</span>
        </button>
        <button
          className={`tool-button ${mode === 'addEdge' ? 'active' : ''}`}
          onClick={() => onModeChange('addEdge')}
          title="Соединить узлы (E)"
        >
          <span className="tool-icon">━</span>
          <span className="tool-label">Дорога</span>
        </button>
        <button
          className={`tool-button ${mode === 'addPlace' ? 'active' : ''}`}
          onClick={() => onModeChange('addPlace')}
          title="Добавить место (T)"
        >
          <span className="tool-icon">📍</span>
          <span className="tool-label">Место</span>
        </button>
        <button
          className={`tool-button ${mode === 'edit' ? 'active' : ''}`}
          onClick={() => onModeChange('edit')}
          title="Редактировать (R)"
        >
          <span className="tool-icon">✏️</span>
          <span className="tool-label">Правка</span>
        </button>
        <button
          className={`tool-button ${mode === 'delete' ? 'active' : ''}`}
          onClick={() => onModeChange('delete')}
          title="Удалить (Del)"
        >
          <span className="tool-icon">🗑️</span>
          <span className="tool-label">Удалить</span>
        </button>
        <button
          className={`tool-button ${mode === 'addLadder' ? 'active' : ''}`}
          onClick={() => onModeChange('addLadder')}
          title="Добавить лестницу (L)"
        >
          <span className="tool-icon">🪜</span>
          <span className="tool-label">Лестница</span>
        </button>
        <button
          className={`tool-button ${mode === 'move' ? 'active' : ''}`}
          onClick={() => onModeChange('move')}
          title="Переместить объект (M)"
        >
          <span className="tool-icon">✋</span>
          <span className="tool-label">Переместить</span>
        </button>
      </div>

      <div className="zoom-controls">
        <button onClick={() => onZoom(0.1)}>Увеличить</button>
        <button onClick={() => onZoom(-0.1)}>Уменьшить</button>
        <button onClick={onResetView}>Сброс</button>
      </div>
    </div>
  );

  return activeTab === 'horizons'
    ? renderHorizonSection()
    : renderToolSection();
}

