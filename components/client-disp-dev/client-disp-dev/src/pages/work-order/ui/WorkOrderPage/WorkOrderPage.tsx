import { useEffect } from 'react';

import { Header, Page } from '@/widgets/page-layout';

import { useGetAllLoadTypeQuery } from '@/shared/api/endpoints/load-types';
import { useGetAllPlacesQuery } from '@/shared/api/endpoints/places';
import { useGetShiftTasksInfiniteQuery } from '@/shared/api/endpoints/shift-tasks';
import { useGetAllVehiclesQuery } from '@/shared/api/endpoints/vehicles';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { useDataLossBlocker } from '@/shared/lib/hooks/useDataLossBlocker';
import { AppRoutes } from '@/shared/routes/router';

import {
  selectAllServerShiftTasks,
  selectDisplayedVehicleIds,
  selectFilteredVehicleIds,
  selectHasChanges,
  selectShiftTasksQueryArg,
} from '../../model/selectors';
import { workOrderActions } from '../../model/slice';
import { useWorkOrderSubmit } from '../../model/submit';
import { useCurrentShift } from '../../model/useCurrentShift';
import { useShiftTasksStream } from '../../model/useShiftTasksStream';
import { WorkOrderContent } from '../WorkOrderContent';
import { WorkOrderToolbar } from '../WorkOrderToolbar';

import styles from './WorkOrderPage.module.css';

/**
 * Представляет компонент страницы «Наряд-задание».
 */
export function WorkOrderPage() {
  const dispatch = useAppDispatch();

  const { isShiftReady, shiftDefinitions, filterState, changeShift } = useCurrentShift();

  const queryArg = useAppSelector(selectShiftTasksQueryArg);

  const vehicleIds = useAppSelector(selectFilteredVehicleIds);
  const displayedVehicleIds = useAppSelector(selectDisplayedVehicleIds);
  const shiftTasks = useAppSelector(selectAllServerShiftTasks);

  // Наряд-задания назначаются по списку всех существующих или выбранных машин
  const { isLoading: isLoadingVehicles, isError: isErrorVehicles } = useGetAllVehiclesQuery();

  // Места используются для полей выпадающего списка → мест погрузки/разгрузки
  const { isLoading: isLoadingPlaces, isError: isErrorPlaces } = useGetAllPlacesQuery();

  // Тип груза используется для расчёта веса, объёма и кол-ва рейсов
  const { isLoading: isCargoLoading, isError: isErrorCargo } = useGetAllLoadTypeQuery();

  const {
    isLoading: isLoadingShiftTasks,
    isFetching: isFetchShiftTasks,
    isError: isErrorShiftTasks,
    refetch: refetchShiftTasks,
  } = useGetShiftTasksInfiniteQuery(queryArg, { skip: !isShiftReady });

  const { submit, isSubmitting } = useWorkOrderSubmit({ refetch: refetchShiftTasks });

  const hasChanges = useAppSelector(selectHasChanges);
  const { forceBlocker } = useDataLossBlocker({ hasUnsavedChanges: hasChanges });

  const highlightedVehicleIds = useShiftTasksStream({ disabled: isSubmitting || !isShiftReady, refetchShiftTasks });

  const isLoading = !isShiftReady || isLoadingVehicles || isLoadingShiftTasks || isLoadingPlaces || isCargoLoading;
  const isError = isErrorVehicles || isErrorShiftTasks || isErrorPlaces || isErrorCargo;
  const hasData = displayedVehicleIds.length > 0;
  // Показываем скелетон при первой загрузке и при повторном запросе, пока новые данные не пришли
  const showSkeleton = isLoading || (isFetchShiftTasks && !hasData);

  useEffect(() => {
    if (isLoading || isFetchShiftTasks || isError || vehicleIds.length === 0) return;

    dispatch(workOrderActions.initializeMissingTasks({ vehicleIds, shiftTasks }));
  }, [isLoading, isFetchShiftTasks, isError, vehicleIds, shiftTasks, dispatch]);

  useEffect(() => {
    return () => {
      dispatch(workOrderActions.resetUnsavedChanges());
    };
  }, [dispatch]);

  return (
    <Page className={styles.sticky_page}>
      <Header
        className={styles.sticky_header}
        routeKey={AppRoutes.WORK_ORDER}
        headerClassName={styles.page_title}
      >
        <WorkOrderToolbar
          onSubmit={submit}
          isLoading={isSubmitting || isFetchShiftTasks}
          confirmDataLoss={forceBlocker}
          shiftDefinitions={shiftDefinitions}
          filterState={filterState}
          changeShift={changeShift}
        />
      </Header>

      <WorkOrderContent
        hasData={hasData}
        isError={isError}
        isInitialLoading={showSkeleton}
        isDisabled={isSubmitting || isFetchShiftTasks}
        vehicleIds={displayedVehicleIds}
        highlightedVehicleIds={highlightedVehicleIds}
      />
    </Page>
  );
}
