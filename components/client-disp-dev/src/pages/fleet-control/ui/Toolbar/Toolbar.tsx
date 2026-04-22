import FleetControlModeIcon from '@/shared/assets/icons/ic-fleet-control-mode.svg?react';
import PlusIcon from '@/shared/assets/icons/ic-plus.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { useResponsiveOverflow } from '@/shared/lib/hooks/useResponsiveOverflow';
import { AppButton } from '@/shared/ui/AppButton';

import { FLEET_CONTROL_MODE } from '../../model/fleet-control-mode';
import { useFleetControlPageContext } from '../../model/FleetControlPageContext';
import { RouteFilter } from '../RouteFilter';

import { ITEMS_PRIORITY, ResponsiveToolbar } from './ResponsiveToolbar';
import styles from './Toolbar.module.css';

/**
 * Представляет компонент панели управления.
 */
export function Toolbar() {
  const { fleetControlMode, handleChangeFleetControlMode, isAddNewRoute, handleAddNewRoute } =
    useFleetControlPageContext();

  const handleAddRout = () => {
    handleAddNewRoute();
  };

  const addRouteButton = (
    <AppButton
      size="xs"
      leftSection={<PlusIcon />}
      onClick={handleAddRout}
      disabled={isAddNewRoute}
    >
      Добавить маршрут
    </AppButton>
  );

  const switchModeButtons = (
    <>
      <AppButton
        size="xs"
        variant={fleetControlMode === FLEET_CONTROL_MODE.VERTICAL ? 'primary' : 'clear'}
        onClick={() => handleChangeFleetControlMode(FLEET_CONTROL_MODE.VERTICAL)}
        onlyIcon
      >
        <FleetControlModeIcon />
      </AppButton>
      <AppButton
        size="xs"
        variant={fleetControlMode === FLEET_CONTROL_MODE.HORIZONTAL ? 'primary' : 'clear'}
        onClick={() => handleChangeFleetControlMode(FLEET_CONTROL_MODE.HORIZONTAL)}
        onlyIcon
      >
        <FleetControlModeIcon className={styles.horizontal_mode_icon} />
      </AppButton>
    </>
  );

  const { containerRef, setItemRef, hiddenCount } = useResponsiveOverflow();

  return (
    <div
      ref={containerRef}
      className={styles.root}
    >
      <div className={styles.actions_container}>
        <div ref={(el) => setItemRef(el, ITEMS_PRIORITY.ADD_ROUTE)}>{addRouteButton}</div>
        <div ref={(el) => setItemRef(el, ITEMS_PRIORITY.ROUTE_FILTER)}>
          <RouteFilter />
        </div>
      </div>
      <div
        ref={(el) => setItemRef(el, ITEMS_PRIORITY.MODE_SWITCHER)}
        className={cn(styles.mode_switcher_container, styles.right)}
      >
        {switchModeButtons}
      </div>

      {hiddenCount > 0 && (
        <ResponsiveToolbar
          hiddenCount={hiddenCount}
          addRouteButton={addRouteButton}
          routesFilter={<RouteFilter withinPortal={false} />}
          modeSwitcher={<div className={styles.mode_switcher_container}>{switchModeButtons}</div>}
        />
      )}
    </div>
  );
}
