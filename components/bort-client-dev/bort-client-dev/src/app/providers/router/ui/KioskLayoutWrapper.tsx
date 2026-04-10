import { Outlet, useLocation } from 'react-router-dom';

import { ArrowControls, KioskKeyboardNav, KioskLeftSidebar } from '@/widgets/kiosk-controls';
import { NewShiftTaskPopupLayer } from '@/widgets/new-shift-task-popup';

import { KioskHeader, KioskLayout } from '@/shared/layouts/KioskLayout';
import { useVehicleEventsSse } from '@/shared/lib/hooks/useVehicleEventsSse';
import { KioskAsideProvider, useKioskAside } from '@/shared/lib/kiosk-aside';
import { KioskHeaderInfoProvider, KioskVehicleHeaderSync, useKioskHeaderInfo } from '@/shared/lib/kiosk-header-info';
import { KioskNavigationProvider } from '@/shared/lib/kiosk-navigation';
import { getRouteMain } from '@/shared/routes/router';

/**
 * Внутренний shell с подпиской на SSE и базовым kiosk layout.
 */
const KioskShell = () => {
  useVehicleEventsSse();
  const { pathname } = useLocation();
  const isMainRoute = pathname === getRouteMain();
  const { headerInfo } = useKioskHeaderInfo();
  const { asideLeft, asideRight, asideLeftWidth, asideRightWidth } = useKioskAside();

  const defaultAsideLeft = isMainRoute ? null : <KioskLeftSidebar />;
  const defaultAsideRight = isMainRoute ? null : <ArrowControls />;
  const defaultAsideWidth = isMainRoute ? '0px' : '90px';

  return (
    <>
      <NewShiftTaskPopupLayer />
      <KioskVehicleHeaderSync />
      <KioskKeyboardNav />
      <KioskLayout
        header={
          <KioskHeader
            locationLabel={headerInfo.locationLabel}
            locationSubLabel={headerInfo.locationSubLabel}
          />
        }
        asideLeft={asideLeft ?? defaultAsideLeft}
        asideRight={asideRight ?? defaultAsideRight}
        asideLeftWidth={asideLeftWidth ?? defaultAsideWidth}
        asideRightWidth={asideRightWidth ?? defaultAsideWidth}
      >
        <Outlet />
      </KioskLayout>
    </>
  );
};

/**
 * Оболочка бортового клиента: kiosk layout и навигация.
 */
export default function KioskLayoutWrapper() {
  return (
    <KioskNavigationProvider>
      <KioskAsideProvider>
        <KioskHeaderInfoProvider>
          <KioskShell />
        </KioskHeaderInfoProvider>
      </KioskAsideProvider>
    </KioskNavigationProvider>
  );
}
