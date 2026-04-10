/**
 * Диалог импорта графов из внешних источников
 */
import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { importGraph, getHorizons } from '../../services/api';
import './ImportDialog.css';

// Поддерживаемые форматы импорта
const SUPPORTED_FORMATS = [
  {
    name: "Structured Levels Format",
    description: "Формат с явной структурой горизонтов"
  },
  {
    name: "Flat Graph Format", 
    description: "Плоский формат с nodes и edges на корневом уровне"
  },
  {
    name: "GeoJSON Format",
    description: "GeoJSON FeatureCollection с Point и LineString features"
  }
];

interface ImportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onImportSuccess: (levelIds: number[]) => void;
}

type ImportStep = 'input' | 'importing' | 'success' | 'error';
type HorizonMode = 'new' | 'existing';

const ImportDialog: React.FC<ImportDialogProps> = ({ isOpen, onClose, onImportSuccess }) => {
  const [step, setStep] = useState<ImportStep>('input');
  const [importMethod, setImportMethod] = useState<'url' | 'json'>('url');
  const [sourceUrl, setSourceUrl] = useState('https://api.qsimmine12-dev.dmi-msk.ru/api/road-net/1');
  const [jsonData, setJsonData] = useState('');
  const [levelMode, setHorizonMode] = useState<HorizonMode>('new');
  const [targetHorizonId, setTargetHorizonId] = useState<number | null>(null);
  const [availableHorizons, setAvailableHorizons] = useState<any[]>([]);
  const [overwriteExisting, setOverwriteExisting] = useState(false);
  const [createNodesWithTags, setCreateNodesWithTags] = useState(true);
  const [tagRadius, setTagRadius] = useState(10);
  const [importResult, setImportResult] = useState<any>(null);
  const [error, setError] = useState<string>('');
  const [showFormats, setShowFormats] = useState(false);

  const handleReset = () => {
    setStep('input');
    setError('');
    setImportResult(null);
  };

  const handleImport = async () => {
    setError('');

    try {
      const requestData: any = {
        overwrite_existing: overwriteExisting,
        create_nodes_with_tags: createNodesWithTags,
        tag_radius: tagRadius
      };

      // Валидация входных данных
      if (importMethod === 'url') {
        if (!sourceUrl.trim()) {
          throw new Error('Введите URL источника данных');
        }
        requestData.source_url = sourceUrl;
      } else {
        if (!jsonData.trim()) {
          throw new Error('Введите JSON данные');
        }
        try {
          requestData.source_data = JSON.parse(jsonData);
        } catch (e) {
          throw new Error('Некорректный JSON формат');
        }
      }

      // Если импортируем в существующий уровень
      if (levelMode === 'existing') {
        if (!targetHorizonId) {
          throw new Error('Выберите горизонт для импорта');
        }
        requestData.horizon_id = targetHorizonId;
      }

      setStep('importing');
      const result = await importGraph(requestData);
      
      if (result.success) {
        setImportResult(result);
        setStep('success');
        
        // Автоматически закрываем только если что-то реально импортировано
        const hasImportedData = result.created_nodes > 0 || result.created_edges > 0 || result.created_tags > 0;
        if (hasImportedData) {
          setTimeout(() => {
            // ✅ Передаем horizon_ids импортированных горизонтов
            onImportSuccess(result.horizon_ids || []);
            onClose();
          }, 2000);
        }
      } else {
        setError(result.message || 'Импорт завершился с ошибками');
        setImportResult(result);
        setStep('error');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Ошибка при импорте');
      setImportResult(err.response?.data);
      setStep('error');
    }
  };

  const handleExampleUrl = () => {
    setSourceUrl('https://api.qsimmine12-dev.dmi-msk.ru/api/road-net/1');
    setImportMethod('url');
  };

  const handleExampleJson = () => {
    const exampleJson = {
      nodes: [
        { id: 1, x: 0, y: 0, z: -50, type: "road" },
        { id: 2, x: 100, y: 0, z: -50, type: "road" },
        { id: 3, x: 100, y: 100, z: -50, type: "junction" },
        { id: 4, x: 0, y: 100, z: -50, type: "road" }
      ],
      edges: [
        { from: 1, to: 2 },
        { from: 2, to: 3 },
        { from: 3, to: 4 },
        { from: 4, to: 1 }
      ],
      tags: [
        { id: 1, x: 0, y: 0, z: -50, radius: 25, name: "Точка A", type: "transit", point_id: "point_a" }
      ]
    };
    setJsonData(JSON.stringify(exampleJson, null, 2));
    setImportMethod('json');
  };

  // Загрузка списка уровней и сброс состояния при открытии диалога
  useEffect(() => {
    if (isOpen) {
      // Сбрасываем состояние при открытии
      setStep('input');
      setError('');
      setImportResult(null);
      setShowFormats(false);
      
      // Загружаем список горизонтов
      loadAvailableHorizons();
    }
  }, [isOpen]);


  const loadAvailableHorizons = async () => {
    try {
      const levels = await getHorizons();
      setAvailableHorizons(levels);
    } catch (err) {
      console.error('Failed to load levels:', err);
    }
  };

  if (!isOpen) return null;

  const modalContent = (
    <div className="modal-overlay" onClick={(e) => {
      // Закрываем только при клике на overlay, не на содержимое
      if (e.target === e.currentTarget) {
        onClose();
      }
    }}>
      <div className="modal import-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>📥 Импорт графа</h3>
          <button onClick={onClose} className="btn-close">&times;</button>
        </div>

        <div className="modal-body">
          {/* Шаг 1: Ввод данных */}
          {step === 'input' && (
            <div className="import-step">
              <div className="import-method-selector">
                <label className="radio-label">
                  <input
                    type="radio"
                    name="importMethod"
                    checked={importMethod === 'url'}
                    onChange={() => setImportMethod('url')}
                  />
                  Из URL
                </label>
                <label className="radio-label">
                  <input
                    type="radio"
                    name="importMethod"
                    checked={importMethod === 'json'}
                    onChange={() => setImportMethod('json')}
                  />
                  JSON данные
                </label>
              </div>

              {importMethod === 'url' && (
                <div className="form-group">
                  <label>URL источника данных:</label>
                  <input
                    type="text"
                    value={sourceUrl}
                    onChange={(e) => setSourceUrl(e.target.value)}
                    placeholder="https://api.qsimmine12-dev.dmi-msk.ru/api/road-net/1"
                    className="form-input"
                  />
                  <button onClick={handleExampleUrl} className="btn-link">
                    Использовать пример URL
                  </button>
                </div>
              )}

              {importMethod === 'json' && (
                <div className="form-group">
                  <label>JSON данные:</label>
                  <textarea
                    value={jsonData}
                    onChange={(e) => setJsonData(e.target.value)}
                    placeholder='{"nodes": [...], "edges": [...], "tags": [...]}'
                    rows={12}
                    className="form-textarea"
                  />
                  <button onClick={handleExampleJson} className="btn-link">
                    Вставить пример JSON
                  </button>
                </div>
              )}

              {/* Выбор горизонта для импорта */}
              <div className="form-group level-selection">
                <label style={{ fontWeight: 600, marginBottom: '10px', display: 'block' }}>
                  Куда импортировать данные:
                </label>
                <div className="import-method-selector">
                  <label className="radio-label">
                    <input
                      type="radio"
                      name="levelMode"
                      checked={levelMode === 'new'}
                      onChange={() => {
                        setHorizonMode('new');
                        setTargetHorizonId(null);
                      }}
                    />
                    Создать новый горизонт
                  </label>
                  <label className="radio-label">
                    <input
                      type="radio"
                      name="levelMode"
                      checked={levelMode === 'existing'}
                      onChange={() => setHorizonMode('existing')}
                    />
                    В существующий горизонт
                  </label>
                </div>

                {levelMode === 'existing' && (
                  <div style={{ marginTop: '10px' }}>
                    <label>Выберите горизонт:</label>
                    <select
                      value={targetHorizonId || ''}
                      onChange={(e) => setTargetHorizonId(e.target.value ? Number(e.target.value) : null)}
                      className="form-input"
                      style={{ marginTop: '5px' }}
                    >
                      <option value="">-- Выберите горизонт --</option>
                      {availableHorizons.map((level: any) => (
                        <option key={level.id} value={level.id}>
                          {level.name} (высота: {level.height}м)
                        </option>
                      ))}
                    </select>
                    {availableHorizons.length === 0 && (
                      <p style={{ color: '#f44336', fontSize: '14px', marginTop: '5px' }}>
                        Нет доступных горизонтов. Создайте горизонт сначала.
                      </p>
                    )}
                  </div>
                )}
              </div>

              {levelMode === 'new' && (
                <div className="form-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={overwriteExisting}
                      onChange={(e) => setOverwriteExisting(e.target.checked)}
                    />
                    Перезаписать существующие горизонты (если высота совпадает)
                  </label>
                </div>
              )}

              {/* Настройки создания вершин */}
              <div className="form-group" style={{ borderTop: '1px solid #ddd', paddingTop: '15px', marginTop: '15px' }}>
                <h4 style={{ fontSize: '16px', marginBottom: '10px' }}>⚙️ Настройки вершин</h4>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={createNodesWithTags}
                    onChange={(e) => setCreateNodesWithTags(e.target.checked)}
                  />
                  Создавать вершины с метками (каждый узел будет иметь метку)
                </label>
                
                {createNodesWithTags && (
                  <div className="form-group" style={{ marginTop: '10px', marginLeft: '25px' }}>
                    <label>
                      Радиус метки (м):
                      <input
                        type="number"
                        min="1"
                        max="100"
                        value={tagRadius}
                        onChange={(e) => setTagRadius(Number(e.target.value))}
                        style={{ width: '100px', marginLeft: '10px' }}
                      />
                    </label>
                    <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                      Рекомендуемое значение: 10-20 метров
                    </p>
                  </div>
                )}
              </div>

              <div className="info-box">
                <p>ℹ️ Импорт поддерживает несколько форматов данных</p>
                <button onClick={() => setShowFormats(!showFormats)} className="btn-link">
                  {showFormats ? 'Скрыть форматы' : 'Показать поддерживаемые форматы'}
                </button>
              </div>

              {showFormats && (
                <div className="formats-info">
                  <h4>Поддерживаемые форматы:</h4>
                  <ul>
                    {SUPPORTED_FORMATS.map((format, idx) => (
                      <li key={idx}>
                        <strong>{format.name}</strong>: {format.description}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Шаг 2: Импортируем */}
          {step === 'importing' && (
            <div className="import-step importing">
              <div className="spinner"></div>
              <p>Импортируем граф...</p>
            </div>
          )}

          {/* Шаг 3: Успех */}
          {step === 'success' && importResult && (
            <div className="import-step success">
              <div className="success-icon">✅</div>
              <h4>Импорт завершен успешно!</h4>
              <div className="result-stats">
                <p>Создано горизонтов: <strong>{importResult.created_horizons}</strong></p>
                <p>Создано узлов: <strong>{importResult.created_nodes}</strong></p>
                <p>Создано рёбер: <strong>{importResult.created_edges}</strong></p>
                <p>Создано меток: <strong>{importResult.created_tags}</strong></p>
              </div>
              <p className="success-message">{importResult.message}</p>
            </div>
          )}

          {/* Шаг 4: Ошибка */}
          {step === 'error' && (
            <div className="import-step error">
              <div className="error-icon">❌</div>
              <h4>Ошибка импорта</h4>
              <p className="error-message">{error}</p>
              {importResult?.errors && importResult.errors.length > 0 && (
                <div className="error-details">
                  <h5>Детали ошибок:</h5>
                  <ul>
                    {importResult.errors.map((err: string, idx: number) => (
                      <li key={idx}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="modal-footer">
          {step === 'input' && (
            <>
              <button onClick={onClose} className="btn-secondary">Отмена</button>
              <button onClick={handleImport} className="btn-primary">Импортировать</button>
            </>
          )}

          {step === 'importing' && (
            <button disabled className="btn-primary">Импортируем...</button>
          )}

          {step === 'success' && (
            <button onClick={onClose} className="btn-primary">Закрыть</button>
          )}

          {step === 'error' && (
            <>
              <button onClick={handleReset} className="btn-secondary">Попробовать снова</button>
              <button onClick={onClose} className="btn-primary">Закрыть</button>
            </>
          )}
        </div>
      </div>
    </div>
  );

  // Рендерим модальное окно в document.body через Portal
  return ReactDOM.createPortal(
    modalContent,
    document.body
  );
};

export default ImportDialog;

