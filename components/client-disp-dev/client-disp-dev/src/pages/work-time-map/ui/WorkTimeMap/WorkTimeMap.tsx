import { Portal } from '@mantine/core';
import { addDays, subDays } from 'date-fns';
import moment, { type MomentInput } from 'moment';
// @ts-expect-error: не видит элемент
import 'moment/dist/locale/ru';
import { useRef, useEffect, useMemo, useCallback } from 'react';
import { DataSet } from 'vis-data';
import { Timeline } from 'vis-timeline/standalone';
import type { DataGroup, TimelineEventPropertiesResult } from 'vis-timeline/standalone';

import { END_SHIFT_OFFSET, getShiftByDate, getShiftsByDate } from '@/entities/shift';
import { getVehicleTypeOrangeIcon } from '@/entities/vehicle';

import {
  type CreateUpdateStateHistoryRequestItem,
  isCycleStateHistory,
  type StateHistory,
  useCreateUpdateStateHistoryMutation,
} from '@/shared/api/endpoints/state-history';
import type { Status } from '@/shared/api/endpoints/statuses';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { cn } from '@/shared/lib/classnames-utils';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { getMapGroupedByField } from '@/shared/lib/get-map-grouped-by-field';
import { hasValue } from '@/shared/lib/has-value';
import { useTimezone } from '@/shared/lib/hooks/useTimezone';
import { toast } from '@/shared/ui/Toast';

import { usePopup } from '../../lib/hooks/usePopup';
import { useZoomControl } from '../../lib/hooks/useZoomControl';
import { isStatusEndOfPrevCycle } from '../../lib/is-status-end-of-cycle';
import type { TimelineItemExtended } from '../../lib/types/timeline-item-extended';
import type { TimelineRangeChangedEvent } from '../../lib/types/timeline-range-changed-event';
import { useWorkTimeMapPageContext } from '../../model/WorkTimeMapPageContext';
import { GroupContextMenu } from '../GroupContextMenu';
import { ItemContextMenu } from '../ItemContextMenu';
import { StatusPopup } from '../StatusPopup';

import styles from './WorkTimeMap.module.css';

/** Идентификатор группы, показывающей смены. */
const VIS_TIMELINE_SHIFT_GROUP_ID = -1;

/** Максимальный зум при котором видны линии смен. */
const VISIBLE_SHIFT_LINE_MAX_ZOOM = 500000000;

/**
 * Представляет компонент "Карта рабочего времени".
 */
export function WorkTimeMap() {
  const {
    stateHistory,
    vehicles,
    statuses,
    shiftDefinitions,
    isLoadingAllStateHistory,
    zoomControlRef,
    vehiclesFilterState: { filterState: vehiclesFilterState },
    dateRangeFilterState: { onFilterChange: onDateRangeFilterChange, filterState: dateRangeFilter },
  } = useWorkTimeMapPageContext();

  const tz = useTimezone();

  const timelineRef = useRef<HTMLDivElement>(null);
  const timelineInstanceRef = useRef<Timeline | null>(null);
  const initialDateRangeRef = useRef(dateRangeFilter);
  const groupsRef = useRef(new DataSet<DataGroup>());
  const itemsRef = useRef(new DataSet<TimelineItemExtended>());
  const shiftLineIds = useRef<string[]>([]);
  const timelineMovingRef = useRef(false);

  const {
    selectedItem: selectedPopupItem,
    handleSelectItem: handleSelectPopupItem,
    handleClose: handleClosePopup,
  } = usePopup<string>();
  const {
    selectedItem: selectedGroup,
    handleSelectItem: handleSelectGroup,
    handleClose: handleCloseContextGroupMenu,
  } = usePopup<number>();
  const {
    selectedItem: selectedContextItemMenu,
    handleSelectItem: handleSelectContextItemMenu,
    handleClose: handleCloseContextItemMenu,
  } = usePopup<string>();

  const closeAllPopups = useCallback(() => {
    handleClosePopup();
    handleCloseContextGroupMenu();
    handleCloseContextItemMenu();
  }, [handleClosePopup, handleCloseContextGroupMenu, handleCloseContextItemMenu]);

  const sortedGroupedByVehicleIdStateHistoryRef = useRef<Map<number, readonly StateHistory[]>>(new Map());

  const sortedGroupedByVehicleIdStateHistory = useMemo(() => {
    const result = new Map<number, StateHistory[]>();

    const groupedByVehicleIdStateHistory = getMapGroupedByField(stateHistory, 'vehicle_id');

    for (const [vehicleId, history] of groupedByVehicleIdStateHistory) {
      const sorted = [...history];

      sorted.sort((a, b) => a.timestamp.localeCompare(b.timestamp));

      result.set(vehicleId, sorted);
    }

    sortedGroupedByVehicleIdStateHistoryRef.current = result;
    return result;
  }, [stateHistory]);

  const statusToPopup = useMemo(() => {
    return stateHistory.find((item) => item.id === selectedPopupItem?.id);
  }, [stateHistory, selectedPopupItem]);

  const nextStatusToPopup = useMemo(() => {
    if (!hasValue(statusToPopup)) {
      return null;
    }

    const vehicleIdStatuses = sortedGroupedByVehicleIdStateHistory.get(statusToPopup.vehicle_id);

    if (!vehicleIdStatuses) {
      return null;
    }

    const nextStatusIndex = vehicleIdStatuses.findIndex((item) => item.id === statusToPopup.id) + 1;

    return vehicleIdStatuses.at(nextStatusIndex) ?? null;
  }, [statusToPopup, sortedGroupedByVehicleIdStateHistory]);

  const selectedStatus = useMemo(() => {
    return stateHistory.find((item) => item.id === selectedContextItemMenu?.id);
  }, [stateHistory, selectedContextItemMenu]);

  const nextStatusAfterSelected = useMemo(() => {
    if (!hasValue(selectedStatus)) {
      return null;
    }

    const vehicleIdStatuses = sortedGroupedByVehicleIdStateHistory.get(selectedStatus.vehicle_id);

    if (!vehicleIdStatuses) {
      return null;
    }

    const nextStatusIndex = vehicleIdStatuses.findIndex((item) => item.id === selectedStatus.id) + 1;

    return vehicleIdStatuses.at(nextStatusIndex) ?? null;
  }, [selectedStatus, sortedGroupedByVehicleIdStateHistory]);

  const selectedCycle = useMemo(() => {
    if (!hasValue(statusToPopup) || !isCycleStateHistory(statusToPopup)) {
      return null;
    }

    const vehicleIdStatuses = sortedGroupedByVehicleIdStateHistory.get(statusToPopup.vehicle_id);

    if (!vehicleIdStatuses) {
      return null;
    }

    const targetCycleId = statusToPopup.cycle_id;

    const stateHistoryByCycleId = hasValue(targetCycleId)
      ? vehicleIdStatuses.filter((item) => isCycleStateHistory(item) && item.cycle_id === targetCycleId)
      : EMPTY_ARRAY;

    return {
      id: statusToPopup.cycle_id,
      firstStatusIdFromSelectedCycle: stateHistoryByCycleId.at(0)?.id,
      lastStatusIdFromSelectedCycle: stateHistoryByCycleId.at(-1)?.id,
    };
  }, [sortedGroupedByVehicleIdStateHistory, statusToPopup]);

  const updateShiftLines = useCallback(() => {
    const timeline = timelineInstanceRef.current;
    if (!timeline) return;

    const range = timeline.getWindow();

    const loopStart = subDays(range.start, 2);
    const loopEnd = addDays(range.end, 2);

    shiftLineIds.current.forEach((id) => {
      timeline.removeCustomTime(id);
    });
    shiftLineIds.current = [];

    const allItems = itemsRef.current.get();
    const oldShifts = allItems.filter((item) => item.className?.includes('shift-block'));

    itemsRef.current.remove(oldShifts.map((s) => s.id));

    const shiftItems: TimelineItemExtended[] = [];

    const currentZoom = zoomControlRef?.current?.getCurrentZoom();

    if (hasValue(currentZoom) && currentZoom < VISIBLE_SHIFT_LINE_MAX_ZOOM) {
      for (let d = new Date(loopStart); d <= loopEnd; d.setDate(d.getDate() + 1)) {
        const shifts = getShiftsByDate(d, shiftDefinitions);

        shifts.forEach((shift) => {
          if (shift.startTime.getTime() >= range.start.getTime() && shift.startTime.getTime() <= range.end.getTime()) {
            const id = `line${shift.shiftNum}-${d.toISOString().split('T')[0]}`;
            timeline.addCustomTime(shift.startTime.getTime(), id);
            shiftLineIds.current.push(id);
          }

          if (shift.startTime.getTime() <= range.end.getTime() && shift.endTime.getTime() >= range.start.getTime()) {
            shiftItems.push({
              id: `shift${shift.shiftNum}-${shift.startTime.toISOString().split('T')[0]}`,
              group: VIS_TIMELINE_SHIFT_GROUP_ID,
              content: `Смена ${shift.shiftNum}, ${tz.format(shift.startTime, 'HH:mm')}-${tz.format(shift.endTime, 'HH:mm')}`,
              start: shift.startTime.getTime(),
              end: shift.endTime.getTime(),
              type: 'background',
              className: 'shift-block shift1',
              editable: false,
            });
          }
        });
      }
    }

    itemsRef.current.add(shiftItems);
  }, [zoomControlRef, shiftDefinitions, tz]);

  const handleRangeChanged = useCallback(
    (event: TimelineRangeChangedEvent) => {
      onDateRangeFilterChange(event.start, event.end);

      updateShiftLines();

      setTimeout(() => {
        timelineMovingRef.current = false;
      });
    },
    [onDateRangeFilterChange, updateShiftLines],
  );

  const handleRangeChange = useCallback(() => {
    timelineMovingRef.current = true;
    closeAllPopups();
  }, [closeAllPopups]);

  const handleClick = useCallback(
    (properties: TimelineEventPropertiesResult) => {
      if (hasValue(properties.item) && typeof properties.item === 'string' && !timelineMovingRef.current) {
        const mouseEvent = properties.event as MouseEvent;

        const targetElement = mouseEvent.target as HTMLElement;

        const itemElement = targetElement.closest('.vis-item');

        if (itemElement) {
          const rect = itemElement.getBoundingClientRect();

          handleSelectPopupItem({
            id: properties.item,
            coordinates: {
              x: mouseEvent.x,
              y: rect.top,
            },
          });
        }
      }
    },
    [handleSelectPopupItem],
  );

  const handleContextMenuClick = useCallback(
    (properties: TimelineEventPropertiesResult) => {
      const mouseEvent = properties.event as MouseEvent;
      mouseEvent?.preventDefault();

      if (
        properties.what === 'group-label' &&
        hasValue(properties.group) &&
        properties.group !== VIS_TIMELINE_SHIFT_GROUP_ID
      ) {
        handleSelectGroup({ id: properties.group, coordinates: { x: mouseEvent.x, y: mouseEvent.y } });
        return;
      }

      if (properties.what === 'item' && hasValue(properties.item) && typeof properties.item === 'string') {
        handleSelectContextItemMenu({ id: properties.item, coordinates: { x: mouseEvent.x, y: mouseEvent.y } });
      }
    },
    [handleSelectContextItemMenu, handleSelectGroup],
  );

  const [createUpdateStateHistoryTrigger, { isLoading: isLoadingCreateUpdateStateHistory }] =
    useCreateUpdateStateHistoryMutation();

  useEffect(() => {
    if (!timelineRef.current || timelineInstanceRef.current) return;

    moment.locale('ru');

    const currentShift = getShiftByDate(new Date(), shiftDefinitions);

    assertHasValue(currentShift, 'Отсутствуют данные текущей смены.');

    const initialRange = initialDateRangeRef.current;
    const hasPersistedRange = initialRange.from.getTime() !== initialRange.to.getTime();
    const rangeStart = hasPersistedRange ? initialRange.from.getTime() : currentShift.startTime.getTime();
    const rangeEnd = hasPersistedRange ? initialRange.to.getTime() : currentShift.endTime.getTime() - END_SHIFT_OFFSET;

    timelineInstanceRef.current = new Timeline(timelineRef.current, itemsRef.current, groupsRef.current, {
      width: '100%',
      height: '100%',
      locale: 'ru',
      stack: false,
      start: rangeStart,
      end: rangeEnd,
      verticalScroll: true,
      horizontalScroll: false,
      zoomKey: 'ctrlKey',
      zoomable: true,
      zoomMin: 60 * 1000,
      zoomMax: 30 * 24 * 60 * 60 * 1000,
      max: Date.now() + 24 * 60 * 60 * 1000,
      moveable: true,
      orientation: 'top',
      groupHeightMode: 'fixed',
      margin: {
        item: { horizontal: 10, vertical: 0 },
        axis: 5,
      },
      moment: (date: MomentInput) => moment(date).utcOffset('+0300'),
      snap: (date) => {
        const mskTime = moment(date).utcOffset('+0300');
        const time = Math.round(mskTime.valueOf() / 1000) * 1000;
        return new Date(time);
      },
      // @ts-expect-error vis-timeline типы несовместимы
      onMoving: (item: TimelineItemExtended, callback: (item: TimelineItemExtended | null) => void) => {
        if (!hasValue(item.id)) {
          return;
        }

        const originalItem = itemsRef.current.get(item.id);
        if (originalItem && item.group !== originalItem.group) {
          callback(null);
          return;
        }

        const prevStatus = hasValue(item.prevItemId) ? itemsRef.current.get(item.prevItemId) : null;
        const nextStatus = hasValue(item.nextItemId) ? itemsRef.current.get(item.nextItemId) : null;

        if (item.className?.includes('live-end') && item.end !== itemsRef.current.get(item.id)?.end) {
          callback(null);
          return;
        }

        if (isInvalidDuration(item, prevStatus, nextStatus)) {
          callback(null);
          return;
        }

        const updates = [];

        if (prevStatus?.end !== item.start) {
          updates.push({ id: prevStatus?.id, end: item.start });
        }

        if (nextStatus?.start !== item.end) {
          updates.push({ id: nextStatus?.id, start: item.end });
        }

        itemsRef.current.update(updates);
        callback(item);
      },
      // @ts-expect-error vis-timeline типы несовместимы
      onMove: async (item: TimelineItemExtended) => {
        const prevStatus = hasValue(item.prevItemId) ? itemsRef.current.get(item.prevItemId) : null;
        const nextStatus = hasValue(item.nextItemId) ? itemsRef.current.get(item.nextItemId) : null;

        const itemGroupNumber = Number(item.group);

        const itemGroup = sortedGroupedByVehicleIdStateHistoryRef.current.get(itemGroupNumber);

        const statusMap = new Map(itemGroup?.map((status) => [status.id, status]));

        const originalStatus = {
          current: typeof item.id === 'string' ? statusMap.get(item.id) || null : null,
          prev: hasValue(item.prevItemId) ? statusMap.get(item.prevItemId) || null : null,
          next: hasValue(item.nextItemId) ? statusMap.get(item.nextItemId) || null : null,
        };

        const updates: CreateUpdateStateHistoryRequestItem[] = [];

        if (
          originalStatus?.current &&
          typeof item.id === 'string' &&
          item.start instanceof Date &&
          new Date(originalStatus.current.timestamp).getTime() !== item.start.getTime()
        ) {
          updates.push({
            id: item.id,
            timestamp: item.start.toISOString(),
            system_name: item.systemName || '',
            system_status: Boolean(item.isSystemStatus),
            cycle_id: item.cycleId,
            is_end_of_cycle: isStatusEndOfPrevCycle(item.cycleId, prevStatus?.cycleId),
          });
        }

        if (
          nextStatus &&
          originalStatus?.next &&
          typeof nextStatus.id === 'string' &&
          nextStatus.start instanceof Date &&
          new Date(originalStatus.next.timestamp).getTime() !== nextStatus.start.getTime()
        ) {
          updates.push({
            id: nextStatus.id,
            timestamp: nextStatus.start.toISOString(),
            system_name: nextStatus.systemName || '',
            system_status: Boolean(nextStatus.isSystemStatus),
            cycle_id: nextStatus.cycleId,
            is_end_of_cycle: isStatusEndOfPrevCycle(nextStatus.cycleId, item.cycleId),
          });
        }

        try {
          const response = createUpdateStateHistoryTrigger({
            vehicle_id: itemGroupNumber,
            items: updates,
          }).unwrap();

          await toast.promise(response, {
            loading: { message: 'Сохранение изменений' },
            success: { message: 'Изменения сохранены' },
            error: { message: 'Ошибка сохранения' },
          });
        } catch {
          const originalStatuses = [originalStatus?.prev, originalStatus?.current, originalStatus?.next].filter(
            hasValue,
          );

          const visItems = originalStatuses.map((status, index, arr) => ({
            id: status.id,
            start: new Date(status.timestamp),
            end: index === arr.length - 1 ? nextStatus?.end : new Date(arr[index + 1].timestamp),
          }));

          itemsRef.current.update(visItems);
        }
      },
    });

    return () => {
      timelineInstanceRef.current?.destroy();
      timelineInstanceRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!timelineInstanceRef.current) return;

    timelineInstanceRef.current.on('rangechanged', handleRangeChanged);
    timelineInstanceRef.current.on('rangechange', handleRangeChange);
    timelineInstanceRef.current.on('click', handleClick);
    timelineInstanceRef.current.on('contextmenu', handleContextMenuClick);

    return () => {
      timelineInstanceRef.current?.off('rangechanged', handleRangeChanged);
      timelineInstanceRef.current?.off('rangechange', handleRangeChange);
      timelineInstanceRef.current?.off('click', handleClick);
      timelineInstanceRef.current?.off('contextmenu', handleContextMenuClick);
    };
  }, [handleClick, handleContextMenuClick, handleRangeChange, handleRangeChanged]);

  useEffect(() => {
    const shiftGroup = {
      id: VIS_TIMELINE_SHIFT_GROUP_ID,
      content: 'Смена',
      className: 'shift-group',
    };

    const filteredVehicles =
      vehiclesFilterState.size > 0 ? vehicles.filter((item) => vehiclesFilterState.has(item.id)) : vehicles;

    const groups = filteredVehicles.map((item) => {
      const icon = getVehicleTypeOrangeIcon(item.vehicle_type);

      const imgHtml = icon ? `<img src="${icon}" alt="vehicle-icon" />` : '';

      return {
        id: item.id,
        content: `<div>
                    ${imgHtml}
                    <span>${item.name}</span>
                  </div>`,
        className: 'vehicle-group',
      };
    });

    groupsRef.current.clear();
    groupsRef.current.add([shiftGroup, ...groups]);
  }, [vehicles, vehiclesFilterState]);

  useEffect(() => {
    const incomingIds = new Set();

    const visItems = [];
    const now = Date.now();

    for (const [vehicleId, stateHistories] of sortedGroupedByVehicleIdStateHistory) {
      const len = stateHistories.length;

      for (let i = 0; i < len; i++) {
        const statusItem = stateHistories[i];
        const isCycleState = isCycleStateHistory(statusItem);
        const cycleId = isCycleState ? statusItem.cycle_id : null;
        incomingIds.add(statusItem.id);

        const isLast = i === len - 1;
        const nextStatus = stateHistories[i + 1];

        const start = new Date(statusItem.timestamp);
        const end = isLast ? now : new Date(nextStatus.timestamp);

        const isSystemStatus = getStatusBySystemName(statuses, statusItem.state)?.system_status;

        visItems.push({
          id: statusItem.id,
          group: vehicleId,
          content: '',
          start,
          end,
          className: cn(
            `state-${statusItem.state}`,
            { 'live-end': isLast },
            `cycle-id-${cycleId}`,
            `state-id-${statusItem.id}`,
          ),
          editable: !isLast && isCycleState,
          prevItemId: stateHistories[i - 1]?.id,
          nextItemId: nextStatus?.id,
          systemName: statusItem.state,
          isSystemStatus: Boolean(isSystemStatus),
          cycleId,
        });
      }
    }

    const currentIds = itemsRef.current.getIds();
    const toRemove = currentIds.filter((id) => !incomingIds.has(String(id)) && !String(id).startsWith('shift'));

    itemsRef.current.update(visItems);

    if (toRemove.length > 0) {
      itemsRef.current.remove(toRemove);
    }
  }, [sortedGroupedByVehicleIdStateHistory, statuses]);

  useEffect(() => {
    const tick = () => {
      if (!itemsRef.current) return;

      const now = Date.now();

      const allItems = itemsRef.current.get();
      const liveItems = allItems.filter((item) => item.className?.includes('live-end'));

      if (liveItems.length > 0) {
        itemsRef.current.update(liveItems.map((item) => ({ id: item.id, end: now })));
      }
    };

    const interval = setInterval(tick, 5000);

    return () => clearInterval(interval);
  }, [stateHistory]);

  useEffect(() => {
    const el = timelineRef.current;
    if (!el || !isLoadingAllStateHistory) return;

    const blockWheel = (e: WheelEvent) => {
      e.preventDefault();
    };

    el.addEventListener('wheel', blockWheel, { passive: false });

    return () => {
      el.removeEventListener('wheel', blockWheel);
    };
  }, [isLoadingAllStateHistory]);

  useZoomControl(itemsRef, timelineInstanceRef, zoomControlRef);

  return (
    <>
      <div
        ref={timelineRef}
        className={cn(styles.root, { ['loader']: isLoadingAllStateHistory || isLoadingCreateUpdateStateHistory })}
      />

      {selectedPopupItem && statusToPopup && (
        <Portal target={document.body}>
          <StatusPopup
            status={statusToPopup}
            nextStatus={nextStatusToPopup}
            coordinates={selectedPopupItem.coordinates}
            onClose={handleClosePopup}
          />
        </Portal>
      )}

      {selectedGroup && (
        <Portal target={document.body}>
          <GroupContextMenu
            groupId={selectedGroup.id}
            coordinates={selectedGroup.coordinates}
            onClose={handleCloseContextGroupMenu}
          />
        </Portal>
      )}

      {selectedContextItemMenu && selectedStatus && (
        <Portal target={document.body}>
          <ItemContextMenu
            status={selectedStatus}
            nextStatus={nextStatusAfterSelected}
            coordinates={selectedContextItemMenu.coordinates}
            onClose={handleCloseContextItemMenu}
          />
        </Portal>
      )}

      <style>
        {statuses
          .map(
            (item) => `
              .state-${item.system_name} {
                background: ${item.color};
                height: 100% !important;
                border: 0 !important;
                border-radius: 0 !important;
                cursor: pointer;

                &.vis-selected {
                  background: ${item.color};
                }
              }
            `,
          )
          .join('\n')}

        {selectedCycle?.id
          ? `
            .cycle-id-${selectedCycle.id} {
              border-top: 3px solid var(--line-fa-connector) !important;
              border-bottom: 3px solid var(--line-fa-connector) !important;
            }

            .cycle-id-${selectedCycle.id}.state-id-${selectedCycle.firstStatusIdFromSelectedCycle} {
              border-left: 3px solid var(--line-fa-connector) !important;
            }

            .cycle-id-${selectedCycle.id}.state-id-${selectedCycle.lastStatusIdFromSelectedCycle} {
              border-right: 3px solid var(--line-fa-connector) !important;
            }
          `
          : ''}

        {statusToPopup
          ? `
            .state-id-${statusToPopup.id}.cycle-id-${selectedCycle?.id} {
              border: 4px solid var(--base-black) !important;
            }
          `
          : ''}
      </style>
    </>
  );
}

/**
 * Проверяет валидность длительности статуса.
 *
 * @param item элемент.
 * @param prevStatus предыдущий статус.
 * @param nextStatus следующий статус.
 */
function isInvalidDuration(
  item: TimelineItemExtended,
  prevStatus: TimelineItemExtended | null,
  nextStatus: TimelineItemExtended | null,
) {
  /** Минимально-допустимая длительность статуса в миллисекундах. */
  const MIN_DURATION = 1000;

  if (item.start instanceof Date && item.end instanceof Date) {
    if (item.end.getTime() - item.start.getTime() < MIN_DURATION) {
      return true;
    }
  }

  if (prevStatus?.start instanceof Date && prevStatus?.end instanceof Date && item.start instanceof Date) {
    const newPrevDuration = item.start.getTime() - prevStatus.start.getTime();
    const originalPrevDuration = prevStatus.end.getTime() - prevStatus.start.getTime();

    if (newPrevDuration < MIN_DURATION && newPrevDuration < originalPrevDuration) {
      return true;
    }
  }

  if (item.end instanceof Date && nextStatus?.start instanceof Date && nextStatus?.end instanceof Date) {
    const newNextDuration = nextStatus.end.getTime() - item.end.getTime();
    const originalNextDuration = nextStatus.end.getTime() - nextStatus.start.getTime();

    if (newNextDuration < MIN_DURATION && newNextDuration < originalNextDuration) {
      return true;
    }
  }

  return false;
}

/**
 * Возвращает статус, на основании системного имени статуса.
 *
 * @param statuses список статусов.
 * @param value значение.
 */
function getStatusBySystemName(statuses: readonly Status[], value: string) {
  return statuses.find((item) => item.system_name === value);
}
