import { createContext, type PropsWithChildren, useCallback, useContext, useMemo, useState } from 'react';

import { hasValue } from '@/shared/lib/has-value';

import { FLEET_CONTROL_MODE, type FleetControlMode } from '../lib/types/fleet-conntrol-mode';
import type { MovingVehicle } from '../lib/types/moving-vehicle';

/** Ключ для сохранения режима отображения в локальном хранилище. */
const STORAGE_KEY = 'asu-gtk-fleet-control-mode';

/** Представляет значение контекста страницы "Управление техникой". */
interface FleetControlPageContextValue {
  /** Возвращает режим отображения страницы "Управление техникой". */
  readonly fleetControlMode: FleetControlMode;
  /** Возвращает делегат, вызываемый при изменении режима отображения страницы "Управление техникой". */
  readonly handleChangeFleetControlMode: (mode: FleetControlMode) => void;
  /** Возвращает режим отображения боковой панели. */
  readonly isOpenSidebar: boolean;
  /** Возвращает делегат, вызываемый при изменении режима отображения боковой панели. */
  readonly handleChangeOpenSidebar: (isOpen: boolean) => void;
  /** Возвращает новый маршрут для создания. */
  readonly isAddNewRoute: boolean;
  /** Возвращает делегат, вызываемый при переходе к созданию нового маршрута. */
  readonly handleAddNewRoute: () => void;
  /** Возвращает делегат, вызываемый удалении нового маршрута. */
  readonly handleRemoveNewRoute: () => void;
  /** Возвращает данные для перемещения оборудования. */
  readonly movingVehicle: MovingVehicle | null;
  /** Возвращает делегат, вызываемый при перемещении оборудования на маршрут. */
  readonly handleMoveVehicleOnRoute: (vehicle: MovingVehicle | null) => void;
  /** Возвращает состояние фильтра по маршрутам. */
  readonly routesFilterState: {
    /** Возвращает список идентификаторов выбранных маршрутов для фильтрации. */
    readonly filterState: Set<string>;
    /** Возвращает делегат, вызываемый при добавлении элементов фильтрации. */
    readonly onAddRoutesFromFilter: (vehicleIds: readonly string[]) => void;
    /** Возвращает делегат, вызываемый при удалении элементов фильтрации. */
    readonly onRemoveRoutesFromFilter: (vehicleIds: readonly string[]) => void;
  };
}

/** Представляет контекст страницы "Управление техникой". */
const FleetControlPageContext = createContext<FleetControlPageContextValue | null>(null);

/** Представляет компонент-провайдер контекста страницы "Управление техникой". */
export function FleetControlPageContextProvider({ children }: Readonly<PropsWithChildren>) {
  const [fleetControlMode, setFleetControlMode] = useState<FleetControlMode>(() => {
    const savedMode = localStorage.getItem(STORAGE_KEY);
    if (
      hasValue(savedMode) &&
      (savedMode === FLEET_CONTROL_MODE.HORIZONTAL || savedMode === FLEET_CONTROL_MODE.VERTICAL)
    ) {
      return savedMode;
    }
    localStorage.setItem(STORAGE_KEY, FLEET_CONTROL_MODE.HORIZONTAL);
    return FLEET_CONTROL_MODE.HORIZONTAL;
  });

  const handleChangeFleetControlMode = useCallback(
    (mode: FleetControlMode) => {
      setFleetControlMode(mode);
      localStorage.setItem(STORAGE_KEY, mode);
    },
    [setFleetControlMode],
  );

  const [isOpenSidebar, setIsOpenSidebar] = useState<boolean>(true);

  const handleChangeOpenSidebar = useCallback(
    (isOpen: boolean) => {
      setIsOpenSidebar(isOpen);
    },
    [setIsOpenSidebar],
  );

  const [isAddNewRoute, setIsAddNewRoute] = useState(false);

  const handleAddNewRoute = useCallback(() => {
    setIsAddNewRoute(true);
  }, [setIsAddNewRoute]);

  const handleRemoveNewRoute = useCallback(() => {
    setIsAddNewRoute(false);
  }, [setIsAddNewRoute]);

  const [movingVehicle, setMovingVehicle] = useState<MovingVehicle | null>(null);

  const handleMoveVehicleOnRoute = useCallback((movingVehicle: MovingVehicle | null) => {
    setMovingVehicle(movingVehicle);
  }, []);

  const [filteredRouteIds, setFilteredRouteIds] = useState<Set<string>>(new Set());

  const onAddRoutesFromFilter = (vehicleIds: readonly string[]) => {
    setFilteredRouteIds((prevSet) => {
      const newSet = new Set(prevSet);
      vehicleIds.forEach((id) => newSet.add(id));
      return newSet;
    });
  };

  const onRemoveRoutesFromFilter = (vehicleIds: readonly string[]) => {
    setFilteredRouteIds((prevSet) => {
      const newSet = new Set(prevSet);
      vehicleIds.forEach((id) => newSet.delete(id));
      return newSet;
    });
  };

  const value = useMemo(() => {
    return {
      fleetControlMode,
      handleChangeFleetControlMode,
      isOpenSidebar,
      handleChangeOpenSidebar,
      isAddNewRoute,
      handleAddNewRoute,
      handleRemoveNewRoute,
      movingVehicle,
      handleMoveVehicleOnRoute,
      routesFilterState: {
        filterState: filteredRouteIds,
        onAddRoutesFromFilter,
        onRemoveRoutesFromFilter,
      },
    };
  }, [
    fleetControlMode,
    handleChangeFleetControlMode,
    isOpenSidebar,
    handleChangeOpenSidebar,
    isAddNewRoute,
    handleAddNewRoute,
    handleRemoveNewRoute,
    movingVehicle,
    handleMoveVehicleOnRoute,
    filteredRouteIds,
  ]);

  return <FleetControlPageContext.Provider value={value}>{children}</FleetControlPageContext.Provider>;
}

/** Представляет хук контекста страницы "Управление техникой". */
export function useFleetControlPageContext() {
  const context = useContext(FleetControlPageContext);
  if (!context) {
    throw new Error('useFleetControlPageContext must be used within FleetControlPageContextProvider');
  }
  return context;
}
