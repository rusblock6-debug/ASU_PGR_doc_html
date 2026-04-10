/**
 * Диалог для создания лестницы между горизонтами
 */
import React, { useState } from 'react';
import { Horizon, GraphNode } from '../../types/graph';
import './LadderDialog.css';

interface LadderDialogProps {
  isOpen: boolean;
  sourceNode: GraphNode | null;
  sourceHorizon: Horizon | null;
  availableHorizons: Horizon[];
  onConfirm: (targetHorizonId: number) => void;
  onConfirmTwoLevels?: (level1Id: number, level2Id: number) => void;
  onCancel: () => void;
  mode?: 'selectTargetLevel' | 'selectTwoLevels';
}

export function LadderDialog({ 
  isOpen, 
  sourceNode, 
  sourceHorizon, 
  availableHorizons, 
  onConfirm, 
  onConfirmTwoLevels,
  onCancel,
  mode = 'selectTargetLevel'
}: LadderDialogProps) {
  const [selectedHorizonId, setSelectedHorizonId] = useState<number | null>(null);
  const [selectedLevel1Id, setSelectedLevel1Id] = useState<number | null>(null);
  const [selectedLevel2Id, setSelectedLevel2Id] = useState<number | null>(null);

  if (!isOpen) {
    return null;
  }

  // Режим выбора двух уровней
  if (mode === 'selectTwoLevels') {
    const handleConfirm = () => {
      if (selectedLevel1Id !== null && selectedLevel2Id !== null && onConfirmTwoLevels) {
        onConfirmTwoLevels(selectedLevel1Id, selectedLevel2Id);
      }
    };

    return (
      <div className="ladder-dialog-overlay" onClick={onCancel}>
        <div className="ladder-dialog" onClick={(e) => e.stopPropagation()}>
          <h3>🪜 Создание лестницы</h3>
          
          <div className="ladder-dialog-content">
            <div className="ladder-target">
              <strong>Выберите два горизонта:</strong>
              <div className="level-list">
                {availableHorizons.length === 0 ? (
                  <div className="no-horizons">Нет доступных горизонтов</div>
                ) : (
                  availableHorizons.map(level => (
                    <div 
                      key={level.id}
                      className={`level-item ${
                        selectedLevel1Id === level.id ? 'selected' : 
                        selectedLevel2Id === level.id ? 'selected-secondary' : ''
                      }`}
                      onClick={() => {
                        if (selectedLevel1Id === null) {
                          setSelectedLevel1Id(level.id);
                        } else if (selectedLevel2Id === null && selectedLevel1Id !== level.id) {
                          setSelectedLevel2Id(level.id);
                        } else if (selectedLevel1Id === level.id) {
                          setSelectedLevel1Id(null);
                        } else if (selectedLevel2Id === level.id) {
                          setSelectedLevel2Id(null);
                        }
                      }}
                    >
                      <div className="level-name">{level.name}</div>
                      <div className="level-height">Высота: {level.height}м</div>
                      {selectedLevel1Id === level.id && <div className="level-badge">Горизонт 1</div>}
                      {selectedLevel2Id === level.id && <div className="level-badge">Горизонт 2</div>}
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="ladder-note">
              <strong>📌 Инструкция:</strong>
              <p>
                1. Выберите первый горизонт (кликните на него)<br/>
                2. Выберите второй горизонт (кликните на него)<br/>
                3. Нажмите "Продолжить"<br/>
                4. Затем выберите узел на первом горизонт<br/>
                5. Затем выберите узел на втором горизонт
              </p>
            </div>
          </div>

          <div className="ladder-dialog-actions">
            <button 
              className="btn-cancel" 
              onClick={onCancel}
            >
              Отмена
            </button>
            <button 
              className="btn-confirm" 
              onClick={handleConfirm}
              disabled={selectedLevel1Id === null || selectedLevel2Id === null}
            >
              Продолжить
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Старый режим (для обратной совместимости)
  if (!sourceNode || !sourceHorizon) {
    return null;
  }

  // Фильтруем горизонты: не показываем текущий горизонт
  const targetHorizons = availableHorizons.filter(level => level.id !== sourceHorizon.id);

  const handleConfirm = () => {
    if (selectedHorizonId !== null) {
      onConfirm(selectedHorizonId);
    }
  };

  return (
    <div className="ladder-dialog-overlay" onClick={onCancel}>
      <div className="ladder-dialog" onClick={(e) => e.stopPropagation()}>
        <h3>🪜 Создание лестницы</h3>
        
        <div className="ladder-dialog-content">
          <div className="ladder-info">
            <strong>Исходная вершина:</strong>
            <div className="node-info">
              <div>ID: {sourceNode.id}</div>
              <div>Координаты: ({sourceNode.x.toFixed(6)}, {sourceNode.y.toFixed(6)})</div>
              <div>Горизонт: {sourceHorizon.name} (высота: {sourceHorizon.height}м)</div>
            </div>
          </div>

          <div className="ladder-target">
            <strong>Выберите целевой горизонт:</strong>
            <div className="level-list">
              {targetHorizons.length === 0 ? (
                <div className="no-horizons">Нет доступных горизонтов для связи</div>
              ) : (
                targetHorizons.map(level => (
                  <div 
                    key={level.id}
                    className={`level-item ${selectedHorizonId === level.id ? 'selected' : ''}`}
                    onClick={() => setSelectedHorizonId(level.id)}
                  >
                    <div className="level-name">{level.name}</div>
                    <div className="level-height">Высота: {level.height}м</div>
                    <div className="level-diff">
                      Разница: {Math.abs(level.height - sourceHorizon.height)}м
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="ladder-note">
            <strong>📌 Примечание:</strong>
            <p>
              Лестница свяжет выбранную вершину с вершиной на целевом горизонте.
              Если на целевом горизонте нет вершины в тех же координатах, она будет создана автоматически.
            </p>
          </div>
        </div>

        <div className="ladder-dialog-actions">
          <button 
            className="btn-cancel" 
            onClick={onCancel}
          >
            Отмена
          </button>
          <button 
            className="btn-confirm" 
            onClick={handleConfirm}
            disabled={selectedHorizonId === null}
          >
            Создать лестницу
          </button>
        </div>
      </div>
    </div>
  );
}

