/**
 * Компонент для отображения панели транспортных средств
 * Используется как в режиме редактирования (светлая тема), так и в режиме просмотра (тёмная тема)
 */
import React, { useMemo, useState, useCallback, useEffect } from 'react';
import { VehiclePosition, Horizon } from '../types/graph';
import { getShiftTask, ShiftTask } from '../services/api';
import './VehiclePanel.css';

interface VehiclePanelProps {
  vehicles: { [key: string]: VehiclePosition };
  horizons: Horizon[];
  onVehicleClick?: (vehicle: VehiclePosition) => void;
  theme?: 'light' | 'dark';
  isOpen?: boolean;
}

export function VehiclePanel({
  vehicles,
  horizons,
  onVehicleClick,
  theme = 'light',
  isOpen = true,
}: VehiclePanelProps) {
  // Гарантируем, что horizons всегда массив
  const safeHorizons = Array.isArray(horizons) ? horizons : [];
  
  const isDark = theme === 'light';
  const vehiclesList = useMemo(() => Object.values(vehicles), [vehicles]);
  const [expandedVehicleId, setExpandedVehicleId] = useState<string | null>(null);

  const handleToggle = useCallback((vehicleId: string) => {
    setExpandedVehicleId((prev) => (prev === vehicleId ? null : vehicleId));
  }, []);

  const getStateLabel = (state?: string): string => {
    if (!state) return '—';
    const stateLabels: Record<string, string> = {
      idle: 'Ожидание',
      moving_empty: 'Движение порожним',
      stopped_empty: 'Остановка порожним',
      loading: 'Погрузка',
      moving_loaded: 'Движение с грузом',
      stopped_loaded: 'Остановка с грузом',
      unloading: 'Разгрузка',
    };
    return stateLabels[state] || state;
  };

  const panelClassName = ['vehicles-panel', isDark ? 'dark' : 'light', isOpen ? 'open' : 'closed'].join(
    ' ',
  );


  return (
    <aside className={panelClassName}>
      <div className="vehicles-panel-inner">
        <div className="vehicles-panel-content">
          {vehiclesList.length === 0 ? (
            <div className="vehicles-panel-empty">Нет данных о транспорте</div>
          ) : (
            vehiclesList.map((vehicle) => {
              const vehicleHeight = vehicle.height ?? null;
              const horizonName =
                vehicleHeight !== null
                  ? safeHorizons.find((level) => Math.abs(level.height - vehicleHeight) < 5)?.name ??
                    `h: ${vehicleHeight}м`
                  : null;
              const hasTag = Boolean(vehicle.currentTag?.point_id);
              const tagName = vehicle.currentTag?.point_name || 'Не определена';
              const tagType = vehicle.currentTag?.point_type || '';
              const telemetryAvailable =
                vehicle.speed != null || vehicle.weight != null || vehicle.fuel != null;
              const isExpanded = expandedVehicleId === vehicle.vehicle_id;
              const stateLabel = vehicle.state ? getStateLabel(vehicle.state) : null;

              return (
                <div
                  key={vehicle.vehicle_id}
                  className={[
                    'vehicle-item',
                    isExpanded ? 'expanded' : 'collapsed',
                    isDark ? 'theme-dark' : 'theme-light',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                >
                  <button
                    type="button"
                    className="vehicle-accordion-trigger"
                    onClick={() => handleToggle(vehicle.vehicle_id)}
                    aria-expanded={isExpanded}
                >
                    <div className="vehicle-trigger-content">
                      <span className="vehicle-id">
                        <img 
                          src="/static/icons/shas.png" 
                          alt="vehicle" 
                          style={{
                            width: '100px',
                            height: '50px',
                            objectFit: 'contain'
                          }}
                        />
                        <span>{vehicle.name || vehicle.vehicle_id}</span>
                      </span>
                      <div className="vehicle-trigger-badges">
                        {stateLabel && <span className="vehicle-chip status">{stateLabel}</span>}
                        {horizonName && <span className="vehicle-chip horizon">{horizonName}</span>}
                  </div>
                    </div>
                    <span className="vehicle-accordion-icon" aria-hidden="true">
                      {isExpanded ? '▾' : '▸'}
                    </span>
                  </button>

                  {isExpanded && (
                    <div className="vehicle-details">
                  {telemetryAvailable && (
                    <div className="vehicle-telemetry">
                      {vehicle.speed != null && (
                        <div>⚡ Скорость: {vehicle.speed.toFixed(1)} км/ч</div>
                      )}
                      {vehicle.weight != null && (
                        <div>⚖️ Вес: {vehicle.weight.toFixed(1)} т</div>
                      )}
                      {vehicle.fuel != null && (
                        <div>⛽ Топливо: {vehicle.fuel.toFixed(0)} л</div>
                      )}
                    </div>
                  )}

                  {vehicle.state && (
                    <div className="vehicle-state">
                          <strong>📊 Статус:</strong> {stateLabel}
                    </div>
                  )}

                  <div
                    className={[
                      'vehicle-tag',
                      hasTag ? 'has-tag' : 'no-tag',
                    ]
                      .filter(Boolean)
                      .join(' ')}
                  >
                    <strong>🏷️ Метка:</strong> {hasTag ? tagName : '❓ Не определена'}
                    {hasTag && tagType && (
                      <div className="vehicle-tag-type">Тип: {tagType}</div>
                    )}
                  </div>

                      <div className="vehicle-actions">
                        {horizonName && (
                          <div className="vehicle-level">
                            <strong>📏 Горизонт:</strong> {horizonName}
                          </div>
                        )}
                        {onVehicleClick && (
                          <button
                            type="button"
                            className="vehicle-focus-btn"
                            onClick={() => onVehicleClick(vehicle)}
                          >
                            Центрировать на карте
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </aside>
  );
}