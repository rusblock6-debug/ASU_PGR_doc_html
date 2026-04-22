import {
  createContext,
  type PropsWithChildren,
  type RefObject,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react';

import type { DateRangeFilter } from '@/features/shift-filter';
import { getDateRangeFromSession, saveDateRangeToSession } from '@/features/shift-filter';

import type { StateHistory } from '@/shared/api/endpoints/state-history';
import { type Status, useGetAllStatusesQuery } from '@/shared/api/endpoints/statuses';
import { useGetAllVehiclesQuery, type Vehicle } from '@/shared/api/endpoints/vehicles';
import { type ShiftDefinition, useGetAllWorkRegimesQuery } from '@/shared/api/endpoints/work-regimes';
import { EMPTY_ARRAY } from '@/shared/lib/constants';

import type { TimelineZoomControl } from '../lib/types/timeline-zoom-control';

import { useStateHistoryDataSource } from './useStateHistoryDataSource';

const COUNT_HOURS_IN_DAY = 24;

const WTM_DATE_FILTER_KEY = 'asu-gtk-work-time-map-date-filter';

/** Представляет значение контекста страницы "Карта рабочего времени". */
interface WorkTimeMapPageContextValue {
  /** Возвращает список исторических записей статусов. */
  readonly stateHistory: readonly StateHistory[];
  /** Возвращает список статусов. */
  readonly statuses: readonly Status[];
  /** Возвращает список транспортных средств. */
  readonly vehicles: readonly Vehicle[];
  /** Возвращает список смен в режиме работы предприятия. */
  readonly shiftDefinitions: readonly ShiftDefinition[];
  /** Возвращает состояние загрузки. */
  readonly isLoading: boolean;
  /** Возвращает состояние загрузки всей истории статусов. */
  readonly isLoadingAllStateHistory: boolean;
  /** Возвращает признак запроса полносменных статусов.  */
  readonly isFullShift: boolean;
  /** Возвращает методы управления масштабом таймлайна. */
  readonly zoomControlRef?: RefObject<TimelineZoomControl | null>;
  /** Возвращает состояние фильтра по транспортным средствам. */
  readonly vehiclesFilterState: {
    /** Возвращает список идентификаторов выбранных транспортных средств для фильтрации. */
    readonly filterState: Set<number>;
    /** Возвращает делегат, вызываемый при добавлении элементов фильтрации. */
    readonly onAddVehiclesFromFilter: (vehicleIds: readonly number[]) => void;
    /** Возвращает делегат, вызываемый при удалении элементов фильтрации. */
    readonly onRemoveVehiclesFromFilter: (vehicleIds: readonly number[]) => void;
  };
  /** Возвращает состояние фильтра по диапазону дат. */
  readonly dateRangeFilterState: {
    /** Возвращает состояние фильтра. */
    readonly filterState: DateRangeFilter;
    /** Возвращает делегат, вызываемый при изменении значения фильтра. */
    readonly onFilterChange: (startDate: Date, endDate: Date) => void;
  };
}

/** Представляет контекст страницы "Карта рабочего времени". */
const WorkTimeMapPageContext = createContext<WorkTimeMapPageContextValue | null>(null);

/** Представляет компонент-провайдер контекста страницы "Карта рабочего времени". */
export function WorkTimeMapPageContextProvider({ children }: Readonly<PropsWithChildren>) {
  const [selectedVehicleIds, setSelectedVehicleIds] = useState<Set<number>>(new Set());

  const onAddVehiclesFromFilter = (vehicleIds: readonly number[]) => {
    setSelectedVehicleIds((prevSet) => {
      const newSet = new Set(prevSet);
      vehicleIds.forEach((id) => newSet.add(id));
      return newSet;
    });
  };

  const onRemoveVehiclesFromFilter = (vehicleIds: readonly number[]) => {
    setSelectedVehicleIds((prevSet) => {
      const newSet = new Set(prevSet);
      vehicleIds.forEach((id) => newSet.delete(id));
      return newSet;
    });
  };

  const { data: vehiclesData, isLoading: isLoadingVehiclesData } = useGetAllVehiclesQuery();

  const vehicles = useMemo(() => Object.values(vehiclesData?.entities ?? {}) ?? EMPTY_ARRAY, [vehiclesData]);

  const { data: statusesData, isLoading: isLoadingStatusesData } = useGetAllStatusesQuery();

  const statuses = useMemo(() => statusesData?.items ?? EMPTY_ARRAY, [statusesData]);

  const { data: workRegimesData } = useGetAllWorkRegimesQuery();

  const shiftDefinitions = useMemo(
    () => workRegimesData?.items.at(0)?.shifts_definition ?? EMPTY_ARRAY,
    [workRegimesData?.items],
  );

  const [dateRangeFilter, setDateRangeFilter] = useState<DateRangeFilter>(
    () => getDateRangeFromSession(WTM_DATE_FILTER_KEY) ?? { from: new Date(), to: new Date() },
  );

  const onDateRangeFilterChange = useCallback((startDate: Date, endDate: Date) => {
    const filter = { from: startDate, to: endDate };
    setDateRangeFilter(filter);
    saveDateRangeToSession(WTM_DATE_FILTER_KEY, filter);
  }, []);

  const isFullShift = useMemo(
    () =>
      (dateRangeFilter.to.getTime() - dateRangeFilter.from.getTime()) / (1000 * 60 * 60) >
      COUNT_HOURS_IN_DAY / shiftDefinitions.length,
    [dateRangeFilter.from, dateRangeFilter.to, shiftDefinitions.length],
  );

  const { stateHistory, isLoadingAllStateHistory } = useStateHistoryDataSource(
    dateRangeFilter,
    selectedVehicleIds,
    shiftDefinitions,
    isFullShift,
  );

  const zoomControlRef = useRef<TimelineZoomControl>(null);

  const value = useMemo(() => {
    return {
      stateHistory,
      statuses,
      vehicles,
      shiftDefinitions,
      isLoading: isLoadingVehiclesData || isLoadingStatusesData,
      isLoadingAllStateHistory,
      isFullShift,
      zoomControlRef,
      vehiclesFilterState: {
        filterState: selectedVehicleIds,
        onAddVehiclesFromFilter,
        onRemoveVehiclesFromFilter,
      },
      dateRangeFilterState: {
        filterState: dateRangeFilter,
        onFilterChange: onDateRangeFilterChange,
      },
    };
  }, [
    stateHistory,
    statuses,
    vehicles,
    shiftDefinitions,
    isLoadingVehiclesData,
    isLoadingStatusesData,
    isLoadingAllStateHistory,
    isFullShift,
    selectedVehicleIds,
    dateRangeFilter,
    onDateRangeFilterChange,
  ]);

  return <WorkTimeMapPageContext.Provider value={value}>{children}</WorkTimeMapPageContext.Provider>;
}

/** Представляет хук контекста страницы "Карта рабочего времени". */
export function useWorkTimeMapPageContext() {
  const context = useContext(WorkTimeMapPageContext);
  if (!context) {
    throw new Error('useWorkTimeMapPageContext must be used within WorkTimeMapPageContextProvider');
  }
  return context;
}
