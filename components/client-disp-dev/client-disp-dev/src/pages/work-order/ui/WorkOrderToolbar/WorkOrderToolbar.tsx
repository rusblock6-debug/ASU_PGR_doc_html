import { type DateRangeFilter, ShiftFilter } from '@/features/shift-filter';
import { VehiclesFilter } from '@/features/vehicles-filter';

import { selectAllVehicles } from '@/entities/vehicle';

import { useLazyPreviewFromPreviousShiftQuery } from '@/shared/api/endpoints/shift-tasks';
import type { ShiftDefinition } from '@/shared/api/endpoints/work-regimes';
import ArrowIcon from '@/shared/assets/icons/ic-arrow-right-with-tail.svg?react';
import ClearIcon from '@/shared/assets/icons/ic-clear.svg?react';
import CopyIcon from '@/shared/assets/icons/ic-copy.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { useConfirm } from '@/shared/lib/confirm';
import { formatNumber } from '@/shared/lib/format-number';
import { hasValueNotEmpty } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { useResponsiveOverflow } from '@/shared/lib/hooks/useResponsiveOverflow';
import { ruPlural } from '@/shared/lib/plural';
import { AppButton } from '@/shared/ui/AppButton';
import { Select } from '@/shared/ui/Select';
import { toast } from '@/shared/ui/Toast';

import {
  selectCurrentShift,
  selectDirtyVehicleIds,
  selectEmptyStatusStats,
  selectHasChanges,
  selectHasEmptyStatusTask,
  selectHasSavedTask,
  selectIsSubmitBlocked,
  selectSelectedStatus,
  selectSelectedVehicleIds,
  selectTotalVolume,
} from '../../model/selectors';
import { workOrderActions } from '../../model/slice';
import type { StatusFilterValue, WarningReasonValue } from '../../model/types';
import { getWarningReasonMessage } from '../../model/warning-reasons';

import { ITEMS_PRIORITY, ResponsiveToolbar } from './ResponsiveToolbar';
import styles from './WorkOrderToolbar.module.css';

const STATUS_OPTIONS: readonly { readonly label: string; readonly value: StatusFilterValue }[] = [
  { label: 'Задания в работе', value: 'active' },
  { label: 'Все задания', value: 'all' },
];

/**
 * Представляет свойства панели для страницы «Наряд-задание».
 */
interface WorkOrderToolbarProps {
  /** Обработчик отправки всех наряд-заданий. */
  readonly onSubmit: () => Promise<void>;
  /** Флаг процесса отправки/загрузки данных. */
  readonly isLoading?: boolean;
  /** Показываем модалку подтверждения потери данных. */
  readonly confirmDataLoss: () => Promise<boolean>;
  /** Определения смен из режима работы. */
  readonly shiftDefinitions: readonly ShiftDefinition[];
  /** Диапазон дат текущей смены для ShiftFilter. */
  readonly filterState: DateRangeFilter;
  /** Переключить смену по дате. */
  readonly changeShift: (startDate: Date) => void;
}

/**
 * Верхняя панель с фильтрами для страницы «Наряд-задание».
 */
export function WorkOrderToolbar({
  onSubmit: onSubmitData,
  isLoading = false,
  confirmDataLoss,
  shiftDefinitions,
  filterState,
  changeShift,
}: WorkOrderToolbarProps) {
  const dispatch = useAppDispatch();
  const formattedVolume = formatNumber(useAppSelector(selectTotalVolume));
  const totalVolume = hasValueNotEmpty(formattedVolume) ? formattedVolume : '0';

  const hasChanges = useAppSelector(selectHasChanges);
  const isSubmitBlocked = useAppSelector(selectIsSubmitBlocked);
  const isSubmitButtonDisabled = !hasChanges || isSubmitBlocked || isLoading;

  const confirm = useConfirm();
  const isActiveActionButtons = useAppSelector(selectHasEmptyStatusTask);
  const emptyStatusStats = useAppSelector(selectEmptyStatusStats);

  const [fetchPreviousData, { isFetching: isPreviewFetching }] = useLazyPreviewFromPreviousShiftQuery();
  const currentShift = useAppSelector(selectCurrentShift);
  const hasSavedTask = useAppSelector(selectHasSavedTask);
  const selectedVehicleIds = useAppSelector(selectSelectedVehicleIds);
  const dirtyVehicleIds = useAppSelector(selectDirtyVehicleIds);
  const selectedStatus = useAppSelector(selectSelectedStatus);

  const vehicles = useAppSelector(selectAllVehicles);

  const validationWarnings = useAppSelector((state) => state.workOrder.validationWarnings);

  const handleShiftFilterChange = async (startDate: Date, _endDate: Date) => {
    const canProceed = await confirmDataLoss();
    if (!canProceed) return;

    changeShift(startDate);
  };

  const handleAddVehicles = (ids: readonly number[]) => {
    dispatch(workOrderActions.addVehiclesToFilter(ids));
  };

  const handleRemoveVehicles = async (ids: readonly number[]) => {
    const dirtySet = new Set(dirtyVehicleIds);
    const removingDirtyVehicles = ids.some((id) => dirtySet.has(id));

    if (removingDirtyVehicles) {
      const canProceed = await confirmDataLoss();
      if (!canProceed) return;
    }

    dispatch(workOrderActions.removeVehiclesFromFilter(ids));
  };

  const handleSelectStatus = async (value: StatusFilterValue | null) => {
    if (!value) return;

    const canProceed = await confirmDataLoss();
    if (!canProceed) return;

    dispatch(workOrderActions.setSelectedStatus(value));
  };

  const handleClearData = async () => {
    const count = emptyStatusStats.vehiclesCount;
    const isConfirmed = await confirm({
      title: `Вы\u00A0действительно хотите очистить данные у\u00A0${count}\u00A0${ruPlural(count, 'объекта', 'объектов', 'объектов')} и\u00A0${emptyStatusStats.tasksCount}\u00A0наряд-заданий?`,
      message: 'Очистятся данные у\u00A0заданий в\u00A0статусе «К\u00A0заполнению».',
      confirmText: 'Очистить',
      cancelText: 'Отмена',
      size: 'md',
    });
    if (!isConfirmed) return;

    dispatch(workOrderActions.clearAllTasks());

    toast.success({ message: 'Наряд-задания очищены' });
  };

  const handleCopyData = async () => {
    if (!currentShift) return;

    if (hasSavedTask) {
      const isConfirmed = await confirm({
        title: `Вы\u00A0действительно хотите скопировать наряд-задания из\u00A0предыдущей смены?`,
        message: 'Скопируются все\u00A0данные, кроме заданий в\u00A0статусе «Отменено»',
        confirmText: 'Скопировать',
        cancelText: 'Отмена',
        size: 'md',
      });
      if (!isConfirmed) return;
    }

    try {
      const result = await fetchPreviousData({
        work_regime_id: currentShift.workRegimeId,
        target_date: currentShift.shiftDate,
        target_shift_num: currentShift.shiftNum,
      }).unwrap();

      dispatch(workOrderActions.applyPreviousTasks(result));

      const vehiclesCount = result.length;
      toast.success({
        message: `Скопированы наряд-задания для ${vehiclesCount} ${ruPlural(vehiclesCount, 'объекта', 'объектов', 'объектов')}`,
      });
    } catch {
      toast.error({ message: 'Не удалось загрузить данные из предыдущей смены' });
    }
  };

  const onSubmit = async () => {
    const tasksWithWarningsCount = Object.keys(validationWarnings).length;

    const warningValues = new Set<WarningReasonValue>();

    for (const validationWarning of Object.values(validationWarnings)) {
      warningValues.add(validationWarning.reason);
    }

    const arrayWarningValues = Array.from(warningValues);

    if (tasksWithWarningsCount > 0 && arrayWarningValues.length > 0) {
      const warningText =
        warningValues.size > 1
          ? 'которые содержат предупреждения'
          : `в которых «${getWarningReasonMessage(arrayWarningValues.at(0))?.slice(0, -1)}»`;

      const isConfirmed = await confirm({
        title: `${tasksWithWarningsCount} ${ruPlural(tasksWithWarningsCount, 'наряд\u2011задание содержит предупреждение', 'наряд\u2011задания содержат предупреждение', 'наряд\u2011заданий содержат предупреждение')}. Вы\u00A0действительно хотите отправить наряд\u2011задания, имеющие предупреждения?`,
        message: `Наряд\u2011задания, ${warningText}, будут отправлены вместе с остальными.`,
        confirmText: 'Отправить',
        cancelText: 'Отмена',
        size: 'md',
      });
      if (!isConfirmed) return;
    }

    void onSubmitData();
  };

  const { containerRef, setItemRef, hiddenCount } = useResponsiveOverflow();

  return (
    <div
      ref={containerRef}
      className={styles.toolbar}
    >
      <div ref={(el) => setItemRef(el, ITEMS_PRIORITY.SHIFT_FILTER)}>
        <ShiftFilter
          shiftDefinitions={shiftDefinitions}
          filterState={filterState}
          onFilterChange={handleShiftFilterChange}
          withCurrentShift
        />
      </div>

      <div ref={(el) => setItemRef(el, ITEMS_PRIORITY.VEHICLES_FILTER)}>
        <VehiclesFilter
          vehicles={vehicles}
          selectedVehicleIds={new Set(selectedVehicleIds)}
          onAddVehiclesFromFilter={handleAddVehicles}
          onRemoveVehiclesFromFilter={handleRemoveVehicles}
        />
      </div>

      <div ref={(el) => setItemRef(el, ITEMS_PRIORITY.TASK_STATUS_FILTER)}>
        <TaskStatusFilter
          handleSelectStatus={handleSelectStatus}
          selectedStatus={selectedStatus}
        />
      </div>

      <div
        ref={(el) => setItemRef(el, ITEMS_PRIORITY.PLANNED_COUNT)}
        className={styles.summary_card_container}
      >
        <PlanedCount totalVolume={totalVolume} />
      </div>

      <div
        ref={(el) => setItemRef(el, ITEMS_PRIORITY.ACTION_BUTTONS)}
        className={styles.action_buttons_container}
      >
        <AppButton
          variant="clear"
          size="xs"
          leftSection={<ClearIcon />}
          onClick={handleClearData}
          disabled={!isActiveActionButtons || isLoading}
        >
          Очистить все
        </AppButton>
        <AppButton
          variant="clear"
          size="xs"
          leftSection={<CopyIcon />}
          onClick={handleCopyData}
          loading={isPreviewFetching}
          disabled={!isActiveActionButtons || isLoading}
        >
          Скопировать из предыдущей смены
        </AppButton>
      </div>

      <div ref={(el) => setItemRef(el, ITEMS_PRIORITY.SUBMIT_BUTTON)}>
        <AppButton
          size="xs"
          leftSection={<ArrowIcon />}
          onClick={onSubmit}
          disabled={isSubmitButtonDisabled}
          loading={isLoading}
        >
          Отправить
        </AppButton>
      </div>

      {hiddenCount > 0 && (
        <ResponsiveToolbar
          hiddenCount={hiddenCount}
          planedCount={<PlanedCount totalVolume={totalVolume} />}
          clearButton={
            <AppButton
              variant="clear"
              size="xs"
              leftSection={<ClearIcon />}
              onClick={handleClearData}
              disabled={!isActiveActionButtons || isLoading}
            >
              Очистить все
            </AppButton>
          }
          copyButton={
            <AppButton
              variant="clear"
              size="xs"
              leftSection={<CopyIcon />}
              onClick={handleCopyData}
              loading={isPreviewFetching}
              disabled={!isActiveActionButtons || isLoading}
            >
              Скопировать из предыдущей смены
            </AppButton>
          }
          submitButton={
            <AppButton
              size="xs"
              leftSection={<ArrowIcon />}
              onClick={onSubmit}
              disabled={isSubmitButtonDisabled}
              loading={isLoading}
            >
              Отправить
            </AppButton>
          }
          taskStatusFilter={
            <TaskStatusFilter
              handleSelectStatus={handleSelectStatus}
              selectedStatus={selectedStatus}
              responsive
            />
          }
          vehiclesFilter={
            <VehiclesFilter
              vehicles={vehicles}
              selectedVehicleIds={new Set(selectedVehicleIds)}
              onAddVehiclesFromFilter={handleAddVehicles}
              onRemoveVehiclesFromFilter={handleRemoveVehicles}
              withinPortal={false}
            />
          }
          shiftFilter={
            <ShiftFilter
              shiftDefinitions={shiftDefinitions}
              filterState={filterState}
              onFilterChange={handleShiftFilterChange}
              withCurrentShift
              withinPortal={false}
            />
          }
        />
      )}
    </div>
  );
}

function TaskStatusFilter({
  handleSelectStatus,
  selectedStatus,
  responsive,
}: {
  readonly handleSelectStatus: (value: StatusFilterValue | null) => void;
  readonly selectedStatus: StatusFilterValue;
  readonly responsive?: boolean;
}) {
  return (
    <Select
      className={cn(styles.status_select, { [styles.status_select_responsive_menu]: responsive })}
      classNames={{
        input: styles.status_select_input,
      }}
      labelPosition="vertical"
      withCheckIcon={false}
      onChange={handleSelectStatus}
      value={selectedStatus}
      data={STATUS_OPTIONS}
      placeholder="Задания в работе"
      variant={responsive ? 'filled' : undefined}
    />
  );
}

function PlanedCount({ totalVolume }: { readonly totalVolume: string }) {
  return (
    <p className={styles.summary_card}>
      Запланировано{' '}
      <span
        className="truncate"
        title={totalVolume}
      >
        {totalVolume}
      </span>{' '}
      м³
    </p>
  );
}
