import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useEffect, useRef, useState } from 'react';

import {
  type RouteDraftFleetControl,
  type RouteFleetControl,
  useDeleteRouteMutation,
} from '@/shared/api/endpoints/fleet-control';
import DragHandleDotsTrashIcon from '@/shared/assets/icons/ic-drag-handle-dots.svg?react';
import TrashIcon from '@/shared/assets/icons/ic-trash.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { useConfirm } from '@/shared/lib/confirm';
import { roundToFixed } from '@/shared/lib/format-number';
import { hasValue } from '@/shared/lib/has-value';
import { AppButton } from '@/shared/ui/AppButton';
import { ErrorMessage } from '@/shared/ui/ErrorMessage';
import { toast } from '@/shared/ui/Toast';
import { Tooltip } from '@/shared/ui/Tooltip';
import { WarningMessage } from '@/shared/ui/WarningMessage';

import { useFleetControlPageDataSource } from '../../../lib/hooks/useFleetControlPageDataSource';
import { FLEET_CONTROL_MODE } from '../../../model/fleet-control-mode';
import { useFleetControlPageContext } from '../../../model/FleetControlPageContext';

import { RouteDetails } from './RouteDetails';
import { RouteHorizontalHeader, RouteVerticalHeader } from './RouteHeader';
import styles from './RouteItem.module.css';

/**
 * Представляет свойства компонента элемента списка маршрутов.
 */
interface RouteItemProps {
  /** Возвращает маршрут. */
  readonly route: RouteFleetControl | RouteDraftFleetControl;
  /** Возвращает признак элемента выбранного для перемещения. */
  readonly isDragging?: boolean;
  /** Возвращает признак элемента отображающего элемент для перемещения. */
  readonly isDragged?: boolean;
  /** Возвращает признак первого элемента списка. */
  readonly isFirst?: boolean;
  /** Возвращает признак последнего элемента списка. */
  readonly isLast?: boolean;
  /** Возвращает признак возможности перемещения. */
  readonly canDrag?: boolean;
}

/**
 * Представляет компонент элемента списка маршрутов.
 */
export function RouteItem({
  route,
  isDragging = false,
  isDragged = false,
  isFirst = false,
  isLast = false,
  canDrag = true,
}: RouteItemProps) {
  const { fleetControlMode, handleRemoveNewRoute } = useFleetControlPageContext();

  const isHorizontalMode = fleetControlMode === FLEET_CONTROL_MODE.HORIZONTAL;

  const { places } = useFleetControlPageDataSource();

  const [deleteRoute] = useDeleteRouteMutation();

  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: route.route_id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const [cargoTypeRouteWarning, setCargoTypeRouteWarning] = useState<string | null>(null);
  const [routeError, setRouteError] = useState<string | null>(null);

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const showRouteError = (text: string) => {
    setRouteError(text);

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(() => {
      setRouteError(null);
    }, 5000);
  };

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const routeFromTitle = places.find((place) => place.id === route.place_a_id)?.name ?? 'Новый маршрут';
  const routeToTitle = places.find((place) => place.id === route.place_b_id)?.name;
  const volumePlan = hasValue(route.volume_plan) ? roundToFixed(route.volume_plan) : null;
  const volumeFact = hasValue(route.volume_fact) ? roundToFixed(route.volume_fact) : null;
  const vehicleCount = route.vehicles?.length;
  const distance = hasValue(route.route_length_m) ? Math.round(route.route_length_m) : null;

  const confirm = useConfirm();

  const handleRemoveRoute = async () => {
    if (route.route_id === 'DRAFT_ROUTE') {
      handleRemoveNewRoute();
      return;
    }

    const confirmed = await confirm({
      title: `Вы действительно хотите удалить маршрут «${routeFromTitle} — ${routeToTitle}»?`,
      confirmText: 'Удалить',
    });

    if (confirmed) {
      const response = deleteRoute(route.route_id).unwrap();

      await toast.promise(response, {
        loading: { message: 'Удаление маршрута' },
        success: { message: 'Маршрут удален' },
        error: { message: 'Ошибка удаления маршрута' },
      });
    }
  };

  const dragButton = (
    <AppButton
      size="xxs"
      variant="clear"
      onlyIcon
      {...attributes}
      {...listeners}
    >
      <Tooltip label="Передвинуть карточку">
        <DragHandleDotsTrashIcon />
      </Tooltip>
    </AppButton>
  );

  const removeButton = (
    <AppButton
      size="xxs"
      variant="clear"
      onlyIcon
      onClick={handleRemoveRoute}
    >
      <Tooltip label="Удалить маршрут">
        <TrashIcon />
      </Tooltip>
    </AppButton>
  );

  const error = hasValue(routeError) && (
    <ErrorMessage
      size="xs"
      message={routeError}
      classNames={styles.attention}
    />
  );

  const warning = !hasValue(routeError) && hasValue(cargoTypeRouteWarning) && (
    <WarningMessage
      size="xs"
      message={cargoTypeRouteWarning}
      classNames={styles.attention}
    />
  );

  return (
    <div
      className={cn(
        styles.root,
        { [styles.vertical]: !isHorizontalMode },
        { [styles.dragging]: isDragging },
        { [styles.dragged]: isDragged },
        { [styles.warning]: !hasValue(routeError) && hasValue(cargoTypeRouteWarning) },
        { [styles.error]: hasValue(routeError) },
        { [styles.first]: isFirst && isHorizontalMode },
        { [styles.last]: isLast && isHorizontalMode },
      )}
      ref={setNodeRef}
      style={style}
    >
      {isHorizontalMode ? (
        <RouteHorizontalHeader
          routeFromTitle={routeFromTitle}
          routeToTitle={routeToTitle}
          volumePlan={volumePlan}
          volumeFact={volumeFact}
          vehicleCount={vehicleCount}
          distance={distance}
          dragButton={canDrag && dragButton}
          removeButton={removeButton}
          warning={warning}
          error={error}
        />
      ) : (
        <RouteVerticalHeader
          routeFromTitle={routeFromTitle}
          routeToTitle={routeToTitle}
          volumePlan={volumePlan}
          volumeFact={volumeFact}
          vehicleCount={vehicleCount}
          distance={distance}
          dragButton={canDrag && dragButton}
          removeButton={removeButton}
        />
      )}
      <RouteDetails
        route={route}
        cargoTypeRouteWarning={cargoTypeRouteWarning}
        setCargoTypeRouteWarning={(value: string | null) => setCargoTypeRouteWarning(value)}
        showRouteError={showRouteError}
      />
      {!isHorizontalMode && error}
      {!isHorizontalMode && warning}
    </div>
  );
}
