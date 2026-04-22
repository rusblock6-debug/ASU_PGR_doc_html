import { useLocation, useNavigate } from 'react-router-dom';

import { getRouteDispatchMap, getRouteMap } from '@/shared/routes/router';
import { FloatingIndicatorGroup } from '@/shared/ui/FloatingIndicator';

/** Конфигурация режимов карты с маршрутами для навигации. */
const MODES = [
  { value: '2D', label: '2D', to: getRouteDispatchMap() },
  { value: '3D', label: '3D', to: getRouteMap() },
] as const;

/**
 * Переключатель режимов карты (2D/3D) с навигацией по маршрутам.
 */
export function MapViewSwitcher() {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  const handleChange = async (value: string) => {
    const mode = MODES.find((m) => m.value === value);
    if (mode) await navigate(mode.to);
  };

  const activeMode = MODES.find((m) => m.to === pathname)?.value ?? '2D';

  return (
    <FloatingIndicatorGroup
      data={MODES}
      value={activeMode}
      onChange={handleChange}
    />
  );
}
