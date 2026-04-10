/**
 * Компонент страницы настроек MQTT и GPS
 */
import React, { useState, useEffect, useRef } from 'react';
import { CoordinateCalibration, OriginPoint } from '../../hooks/useSettings';
import { getVehicles, EnterpriseVehicle } from '../../services/api';

interface SettingsPageProps {
  coordinateCalibration: CoordinateCalibration;
  onCoordinateCalibrationChange: (calibration: CoordinateCalibration) => void;
  onCancel: () => void;
  onSave: () => void;
  onStartPointSelection?: (pointNumber: 1 | 2) => void;
}

export function SettingsPage({
  coordinateCalibration,
  onCoordinateCalibrationChange,
  onCancel,
  onSave,
}: SettingsPageProps) {
  const [vehicles, setVehicles] = useState<EnterpriseVehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Загружаем список машин при монтировании (только один раз)
  useEffect(() => {
    const loadVehicles = async () => {
      try {
        setLoading(true);
        setError(null);
        const vehiclesList = await getVehicles(1); // enterprise_id = 1 по умолчанию
        setVehicles(vehiclesList);
      } catch (err) {
        console.error('Failed to load vehicles:', err);
        setError('Не удалось загрузить список машин. Проверьте подключение к enterprise-service.');
      } finally {
        setLoading(false);
      }
    };
    loadVehicles();
  }, []);
  return (
    <div className="settings-page">
      <div className="settings-container">
        <h2>Автопарк</h2>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '14px', marginBottom: '16px' }}>
          Список машин из enterprise-service. Все машины отображаются в визуализации.
        </p>
        
        {loading && (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
            Загрузка списка машин...
          </div>
        )}
        
        {error && (
          <div style={{ 
            padding: '16px', 
            background: 'rgba(255, 0, 0, 0.1)', 
            borderRadius: '8px', 
            color: 'var(--color-accent)',
            marginBottom: '16px',
            borderLeft: '4px solid var(--color-accent)'
          }}>
            ⚠️ {error}
          </div>
        )}
        
        {!loading && !error && vehicles.length === 0 && (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
            Машины не найдены. Убедитесь, что в enterprise-service добавлены машины.
          </div>
        )}
        
        {!loading && !error && vehicles.length > 0 && (
          <div style={{ 
            marginBottom: '32px', 
            padding: '20px', 
            background: 'var(--color-bg-elevated)', 
            borderRadius: '8px', 
            border: '1px solid var(--color-border)' 
          }}>
            <div style={{ 
              marginBottom: '16px',
              fontSize: '15px', 
              fontWeight: '600', 
              color: 'var(--color-text-secondary)' 
            }}>
              Всего машин: {vehicles.length}
            </div>
            
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', 
              gap: '12px',
              maxHeight: '400px',
              overflowY: 'auto',
              padding: '8px'
            }}>
              {vehicles.map((vehicle) => (
                <div
                  key={vehicle.id}
                  style={{
                    padding: '12px',
                    background: 'var(--color-bg-surface)',
                    borderRadius: '6px',
                    border: '1px solid var(--color-border)'
                  }}
                >
                  <div style={{ fontWeight: '600', color: 'var(--color-text-primary)', marginBottom: '4px' }}>
                    {vehicle.name}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                    <div>Vehicle ID: <strong>{vehicle.id}</strong></div>
                    <div>Тип: {vehicle.vehicle_type === 'pdm' ? 'ПДМ' : vehicle.vehicle_type === 'shas' ? 'ШАС' : vehicle.vehicle_type}</div>
                    {vehicle.model && <div>Модель: {vehicle.model.name}</div>}
                    {vehicle.capacity_tons && <div>Грузоподъемность: {vehicle.capacity_tons} т</div>}
                    {vehicle.payload_tons && <div>Грузоподъемность: {vehicle.payload_tons} т</div>}
                    {vehicle.dump_body_volume_m3 && <div>Объем кузова: {vehicle.dump_body_volume_m3} м³</div>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        <h2 style={{ marginTop: '32px' }}>Калибровка GPS координат (метрическая проекция)</h2>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '14px', marginBottom: '16px' }}>
          Укажите одну опорную точку (origin) для конверсии GPS координат в метры
        </p>
        
        <div className="form-group">
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-text-secondary)' }}>
            <input
              type="checkbox"
              checked={coordinateCalibration.enabled}
              onChange={(e) => onCoordinateCalibrationChange({
                ...coordinateCalibration,
                enabled: e.target.checked
              })}
            />
            Включить GPS режим (метрическая проекция)
          </label>
        </div>
        
        {coordinateCalibration.enabled && (
          <div style={{ marginTop: '16px', padding: '20px', background: 'var(--color-bg-elevated)', borderRadius: '8px', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }}>
            <h3 style={{ fontSize: '18px', marginBottom: '16px', color: 'var(--color-accent)', fontWeight: 'bold' }}>
              📍 Опорная точка (Origin)
            </h3>
            
            {/* GPS координаты */}
            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ fontSize: '15px', marginBottom: '12px', color: 'var(--color-text-secondary)', fontWeight: '600' }}>
                🌍 GPS координаты опорной точки:
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '14px', fontWeight: '500', color: 'var(--color-text-secondary)' }}>Широта (Latitude):</label>
                  <input
                    type="number"
                    value={coordinateCalibration.origin?.gpsLat || ''}
                    onChange={(e) => {
                      const origin = coordinateCalibration.origin || { gpsLat: 0, gpsLon: 0, canvasX: 0, canvasY: 0, canvasZ: 0 };
                      onCoordinateCalibrationChange({
                        ...coordinateCalibration,
                        origin: { ...origin, gpsLat: parseFloat(e.target.value) || 0 }
                      });
                    }}
                    placeholder="58.175000"
                    step="0.000001"
                  />
                  <small style={{ color: 'var(--color-text-muted)' }}>Например: 58.175000</small>
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '14px', fontWeight: '500', color: 'var(--color-text-secondary)' }}>Долгота (Longitude):</label>
                  <input
                    type="number"
                    value={coordinateCalibration.origin?.gpsLon || ''}
                    onChange={(e) => {
                      const origin = coordinateCalibration.origin || { gpsLat: 0, gpsLon: 0, canvasX: 0, canvasY: 0, canvasZ: 0 };
                      onCoordinateCalibrationChange({
                        ...coordinateCalibration,
                        origin: { ...origin, gpsLon: parseFloat(e.target.value) || 0 }
                      });
                    }}
                    placeholder="59.820000"
                    step="0.000001"
                  />
                  <small style={{ color: 'var(--color-text-muted)' }}>Например: 59.820000</small>
                </div>
              </div>
            </div>
            
            {/* Canvas координаты */}
            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ fontSize: '15px', marginBottom: '12px', color: 'var(--color-text-secondary)', fontWeight: '600' }}>
                📐 Canvas координаты этой точки (в метрах):
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '14px', fontWeight: '500', color: 'var(--color-text-secondary)' }}>X (восток):</label>
                  <input
                    type="number"
                    value={coordinateCalibration.origin?.canvasX ?? ''}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      const origin = coordinateCalibration.origin || { gpsLat: 0, gpsLon: 0, canvasX: 0, canvasY: 0, canvasZ: 0 };
                      onCoordinateCalibrationChange({
                        ...coordinateCalibration,
                        origin: { ...origin, canvasX: isNaN(val) ? 0 : val }
                      });
                    }}
                    placeholder="0"
                    step="10"
                  />
                  <small style={{ color: 'var(--color-text-muted)' }}>метров</small>
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '14px', fontWeight: '500', color: 'var(--color-text-secondary)' }}>Y (север):</label>
                  <input
                    type="number"
                    value={coordinateCalibration.origin?.canvasY ?? ''}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      const origin = coordinateCalibration.origin || { gpsLat: 0, gpsLon: 0, canvasX: 0, canvasY: 0, canvasZ: 0 };
                      onCoordinateCalibrationChange({
                        ...coordinateCalibration,
                        origin: { ...origin, canvasY: isNaN(val) ? 0 : val }
                      });
                    }}
                    placeholder="0"
                    step="10"
                  />
                  <small style={{ color: 'var(--color-text-muted)' }}>метров</small>
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '14px', fontWeight: '500', color: 'var(--color-text-secondary)' }}>Z (высота):</label>
                  <input
                    type="number"
                    value={coordinateCalibration.origin?.canvasZ ?? ''}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      const origin = coordinateCalibration.origin || { gpsLat: 0, gpsLon: 0, canvasX: 0, canvasY: 0, canvasZ: 0 };
                      onCoordinateCalibrationChange({
                        ...coordinateCalibration,
                        origin: { ...origin, canvasZ: isNaN(val) ? 0 : val }
                      });
                    }}
                    placeholder="-100"
                    step="10"
                  />
                  <small style={{ color: 'var(--color-text-muted)' }}>метров</small>
                </div>
              </div>
            </div>
            
            {/* Статус калибровки */}
            <div style={{ 
              marginTop: '20px', 
              padding: '16px', 
              background: coordinateCalibration.origin?.gpsLat && coordinateCalibration.origin?.gpsLon ? 'rgba(209, 92, 41, 0.18)' : 'rgba(159, 159, 159, 0.18)',
              borderRadius: '8px',
              fontSize: '14px',
              color: coordinateCalibration.origin?.gpsLat && coordinateCalibration.origin?.gpsLon ? 'var(--color-text-secondary)' : 'var(--color-accent)',
              borderLeft: '4px solid',
              borderColor: coordinateCalibration.origin?.gpsLat && coordinateCalibration.origin?.gpsLon ? 'rgba(159, 159, 159, 0.45)' : 'var(--color-accent)'
            }}>
              {coordinateCalibration.origin?.gpsLat && coordinateCalibration.origin?.gpsLon 
                ? '✅ Калибровка настроена! GPS координаты будут конвертироваться в метры на карте.'
                : '⚠️ ОБЯЗАТЕЛЬНО укажите GPS координаты опорной точки! Без них truck не будет отображаться.'}
            </div>
            
            {/* Дополнительное предупреждение если GPS = 0 */}
            {coordinateCalibration.origin && 
             (coordinateCalibration.origin.gpsLat === 0 || coordinateCalibration.origin.gpsLon === 0) && (
              <div style={{
                marginTop: '12px',
                padding: '12px',
                background: 'rgba(209, 92, 41, 0.18)',
                borderRadius: '8px',
                fontSize: '14px',
                color: 'var(--color-accent)',
                borderLeft: '4px solid rgba(209, 92, 41, 0.5)'
              }}>
                ❌ <strong>ОШИБКА:</strong> GPS координаты не могут быть 0.000000°!<br/>
                Укажите реальные координаты вашего карьера/шахты.<br/>
                Например: Lat: 58.175073, Lon: 59.809301
              </div>
            )}
            
            {/* Инструкция с примером */}
            <details style={{ marginTop: '20px', fontSize: '14px', background: 'var(--color-bg-surface)', padding: '12px', borderRadius: '8px', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }}>
              <summary style={{ cursor: 'pointer', fontWeight: 'bold', color: 'var(--color-text-secondary)' }}>
                💡 Как настроить калибровку? (Метрическая проекция)
              </summary>
              <div style={{ marginTop: '12px', paddingLeft: '8px' }}>
                <p style={{ marginBottom: '12px', color: 'var(--color-text-secondary)', lineHeight: '1.6' }}>
                  <strong>Метрическая проекция</strong> конвертирует GPS координаты (градусы) в метры на вашей карте.
                  Это физически правильный подход!
                </p>
                <ol style={{ paddingLeft: '20px', color: 'var(--color-text-muted)', lineHeight: '1.8' }}>
                  <li>Найдите <strong>одну известную точку</strong> на карте (например, угол карьера или начало дороги)</li>
                  <li>Запишите её <strong>Canvas координаты</strong> (X, Y, Z) - это координаты на вашей карте в метрах</li>
                  <li>Узнайте <strong>GPS координаты</strong> этой же точки (lat, lon) - можно из навигатора или карты</li>
                  <li>Введите эти значения выше</li>
                  <li>Сохраните настройки</li>
                </ol>
                <div style={{ 
                  marginTop: '16px', 
                  padding: '12px', 
                  background: 'rgba(255, 127, 63, 0.12)', 
                  borderRadius: '6px',
                  borderLeft: '3px solid var(--color-accent)'
                }}>
                  <p style={{ fontWeight: 'bold', marginBottom: '8px', color: 'var(--color-text-secondary)' }}>📝 Пример:</p>
                  <p style={{ color: 'var(--color-text-muted)', fontSize: '13px', lineHeight: '1.6' }}>
                    <strong>Опорная точка:</strong><br/>
                    GPS: 58.175000°, 59.820000°<br/>
                    Canvas: X=0м, Y=0м, Z=-100м<br/><br/>
                    
                    <strong>Truck на GPS: 58.176500°, 59.821500°</strong><br/>
                    Разница: +0.0015° север, +0.0015° восток<br/>
                    В метрах: ~167м север, ~88м восток<br/>
                    <strong>→ Canvas: X=88м, Y=167м ✅</strong>
                  </p>
                </div>
              </div>
            </details>
          </div>
        )}
        
        <div className="form-actions">
          <button onClick={onCancel}>Отмена</button>
          <button 
            className="btn-primary" 
            onClick={() => {
              // Валидация перед сохранением
              if (coordinateCalibration.enabled) {
                if (!coordinateCalibration.origin?.gpsLat || !coordinateCalibration.origin?.gpsLon) {
                  alert('⚠️ GPS координаты опорной точки не заполнены!\n\nБез них truck не будет отображаться на карте.');
                  return;
                }
                if (coordinateCalibration.origin.gpsLat === 0 || coordinateCalibration.origin.gpsLon === 0) {
                  alert('❌ GPS координаты не могут быть 0.000000°!\n\nУкажите реальные координаты вашего карьера/шахты.\nНапример: Lat: 58.175073, Lon: 59.809301');
                  return;
                }
              }
              // Сохраняем настройки
              onSave();
            }}
          >
            Сохранить
          </button>
        </div>
      </div>
    </div>
  );
}



