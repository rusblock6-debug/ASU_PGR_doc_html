import { useEffect, useMemo, useState } from 'react';

import { Header, Page } from '@/widgets/page-layout';

import { type DateRangeFilter, ShiftFilter } from '@/features/shift-filter';
import { getDateRangeFromSession, saveDateRangeToSession } from '@/features/shift-filter';

import { getPlacesOptionsToSelect } from '@/entities/place';
import { END_SHIFT_OFFSET, getShiftByDate } from '@/entities/shift';

import { useGetAllPlacesQuery } from '@/shared/api/endpoints/places';
import {
  type EnrichedTrip,
  type Trip,
  useCreateTripMutation,
  useDeleteTripMutation,
  useGetTripsInfiniteQuery,
  useUpdateTripMutation,
} from '@/shared/api/endpoints/trips';
import { useGetAllVehiclesQuery } from '@/shared/api/endpoints/vehicles';
import { useGetAllWorkRegimesQuery } from '@/shared/api/endpoints/work-regimes';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { AppRoutes } from '@/shared/routes/router';
import { ControlPanel, Table, TableProvider } from '@/shared/ui/Table';
import { toast } from '@/shared/ui/Toast';
import type { SelectOption } from '@/shared/ui/types';

import { getBaseColumns } from '../../model/trip-columns';

import styles from './TripEditorPage.module.css';

const TRIPS_POLLING_INTERVAL = 10_000;

const TRIP_DATE_FILTER_KEY = 'asu-gtk-trip-editor-date-filter';

/**
 * Представляет компонент страницы «Управление рейсами».
 */
export function TripEditorPage() {
  const { data: vehiclesData } = useGetAllVehiclesQuery();
  const { data: placesData } = useGetAllPlacesQuery();
  const { data: workRegimesData } = useGetAllWorkRegimesQuery();

  const [createTrip] = useCreateTripMutation();
  const [updateTrip] = useUpdateTripMutation();
  const [deleteTrip] = useDeleteTripMutation();

  const shiftDefinitions = useMemo(
    () => workRegimesData?.items.at(0)?.shifts_definition ?? EMPTY_ARRAY,
    [workRegimesData?.items],
  );

  const [dateRangeFilter, setDateRangeFilter] = useState<DateRangeFilter | undefined>(
    () => getDateRangeFromSession(TRIP_DATE_FILTER_KEY) ?? undefined,
  );

  useEffect(() => {
    if (!dateRangeFilter && shiftDefinitions.length > 0) {
      const currentShift = getShiftByDate(new Date(), shiftDefinitions);

      if (currentShift) {
        const endDateWithCorrection = new Date(currentShift.endTime.getTime() - END_SHIFT_OFFSET);
        const filter = { from: currentShift.startTime, to: endDateWithCorrection };

        setDateRangeFilter(filter);
        saveDateRangeToSession(TRIP_DATE_FILTER_KEY, filter);
      }
    }
  }, [dateRangeFilter, shiftDefinitions]);

  const onDateRangeFilterChange = (startDate: Date, endDate: Date) => {
    const filter = { from: startDate, to: endDate };
    setDateRangeFilter(filter);
    saveDateRangeToSession(TRIP_DATE_FILTER_KEY, filter);
  };

  const vehicleOptions: SelectOption[] = useMemo(() => {
    if (!vehiclesData?.entities) return [];

    return vehiclesData.ids.map((id) => ({
      value: String(vehiclesData.entities[id].id),
      label: vehiclesData.entities[id].name,
    }));
  }, [vehiclesData]);

  const placesOptions = useMemo(() => getPlacesOptionsToSelect(placesData?.items), [placesData]);

  const columns = useMemo(() => getBaseColumns(vehicleOptions, placesOptions), [vehicleOptions, placesOptions]);

  const dateFilters = useMemo(() => {
    return {
      from_date: dateRangeFilter?.from.toISOString(),
      to_date: dateRangeFilter?.to.toISOString(),
    };
  }, [dateRangeFilter]);

  const {
    data: tripsData,
    isLoading,
    isFetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useGetTripsInfiniteQuery(dateFilters, {
    pollingInterval: TRIPS_POLLING_INTERVAL,
    skip: !dateRangeFilter,
  });

  const trips = useMemo(() => {
    if (!tripsData?.pages || !vehiclesData?.entities) return [];

    return tripsData.pages.flatMap((page) =>
      page.items.map((trip) => {
        const vehicle = vehiclesData.entities[trip.vehicle_id];

        return {
          ...trip,
          vehicle_name: vehicle.name,
        } as EnrichedTrip;
      }),
    );
  }, [tripsData?.pages, vehiclesData?.entities]);

  const total = tripsData?.pages[0]?.total ?? 0;

  const handleScrollToBottom = () => {
    if (!isFetching && !isFetchingNextPage && hasNextPage) {
      void fetchNextPage();
    }
  };

  const handleAdd = async (newTrip: Partial<Trip>) => {
    const {
      vehicle_id: vehicleId,
      loading_place_id: loadingPlaceId,
      unloading_place_id: unloadingPlaceId,
      cycle_started_at: cycleStartedAt,
      cycle_completed_at: cycleCompletedAt,
      change_amount: changeAmount,
    } = newTrip;

    assertHasValue(vehicleId, 'vehicle_id is required');
    assertHasValue(loadingPlaceId, 'loading_place_id is required');
    assertHasValue(unloadingPlaceId, 'unloading_place_id is required');
    assertHasValue(cycleStartedAt, 'cycle_started_at is required');
    assertHasValue(cycleCompletedAt, 'cycle_completed_at is required');

    const vehicleName = vehicleOptions.find((item) => item.value === String(vehicleId))?.label;

    const request = createTrip({
      vehicle_id: vehicleId,
      loading_place_id: loadingPlaceId,
      unloading_place_id: unloadingPlaceId,
      cycle_started_at: cycleStartedAt,
      cycle_completed_at: cycleCompletedAt,
      change_amount: hasValue(changeAmount) ? changeAmount : null,
    }).unwrap();

    await toast.promise(request, {
      loading: {
        message: vehicleName ? `Добавление нового рейса для «${vehicleName}»` : 'Добавление объекта',
      },
      success: {
        message: vehicleName ? `Добавлен новый рейс для «${vehicleName}»` : 'Объект добавлен в таблицу',
      },
      error: {
        message: 'Ошибка добавления',
      },
    });
  };

  const handleEdit = async (id: string | number, updatedData: Partial<Trip>) => {
    await updateTrip({
      tripId: String(id),
      body: {
        vehicle_id: updatedData.vehicle_id,
        loading_place_id: hasValue(updatedData.loading_place_id) ? updatedData.loading_place_id : undefined,
        loading_timestamp: hasValue(updatedData.loading_timestamp) ? updatedData.loading_timestamp : undefined,
        unloading_place_id: hasValue(updatedData.unloading_place_id) ? updatedData.unloading_place_id : undefined,
        unloading_timestamp: hasValue(updatedData.unloading_timestamp) ? updatedData.unloading_timestamp : undefined,
        cycle_started_at: hasValue(updatedData.cycle_started_at) ? updatedData.cycle_started_at : undefined,
        cycle_completed_at: hasValue(updatedData.cycle_completed_at) ? updatedData.cycle_completed_at : undefined,
        change_amount: hasValue(updatedData.change_amount) ? updatedData.change_amount : null,
      },
    }).unwrap();
  };

  const handleDelete = async (ids: (string | number)[]) => {
    await Promise.all(ids.map((id) => deleteTrip(String(id)).unwrap()));
  };

  return (
    <Page variant="table">
      <TableProvider
        data={trips}
        columns={columns}
        total={total}
        storageKey="asu-gtk-trip"
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDelete}
        getRowId={(row) => row.cycle_id}
        formAddTitle="Hовый рейс"
        formEditTitle="Редактировать рейс"
      >
        <Header
          headerClassName="table-header"
          routeKey={AppRoutes.TRIP_EDITOR}
        >
          <ControlPanel
            centerContent={
              <div className={styles.shift_filter_container}>
                <ShiftFilter
                  shiftDefinitions={shiftDefinitions}
                  filterState={dateRangeFilter}
                  onFilterChange={onDateRangeFilterChange}
                  mode="multiShift"
                  withCurrentShift
                />
              </div>
            }
          />
        </Header>

        <div className="table-wrapper">
          <Table
            data={trips}
            columns={columns}
            isLoading={isLoading || (isFetching && trips.length > 0)}
            onScrollToBottom={handleScrollToBottom}
            scrollResetKey={`${dateRangeFilter?.from.getTime()}${dateRangeFilter?.to.getTime()}`}
          />
        </div>
      </TableProvider>
    </Page>
  );
}
