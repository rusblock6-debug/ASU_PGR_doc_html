/**
 * Компонент панели отслеживания транспортных средств
 * ОБЁРТКА для единого VehiclePanel с светлой темой (для режима редактирования)
 */
import React from 'react';
import { VehiclePanel } from '../VehiclePanel';
import { VehiclePosition, Horizon } from '../../types/graph';

interface VehiclesPanelProps {
  vehicles: { [key: string]: VehiclePosition };
  onVehicleClick: (vehicle: VehiclePosition) => void;
  horizons?: Horizon[];
  isOpen?: boolean;
  theme?: 'light' | 'dark';
}

export function VehiclesPanel({
  vehicles,
  onVehicleClick,
  horizons = [],
  isOpen = true,
  theme = 'light',
}: VehiclesPanelProps) {
  return (
    <VehiclePanel
      vehicles={vehicles}
      horizons={horizons}
      onVehicleClick={onVehicleClick}
      theme={theme}
      isOpen={isOpen}
    />
  );
}
