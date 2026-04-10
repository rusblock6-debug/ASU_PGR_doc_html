import { useNavigate } from 'react-router-dom';

import { getRouteMain } from '@/shared/routes/router';
import { KioskBackButton } from '@/shared/ui/KioskBackButton';

import { ConfirmButton } from '../ConfirmButton';

/**
 * Левая зона kiosk-управления: «назад» вверху (всегда на главный экран) и подтверждение внизу.
 */
export const KioskLeftSidebar = () => {
  const navigate = useNavigate();

  return (
    <>
      <KioskBackButton onClick={() => void navigate(getRouteMain())} />
      <ConfirmButton />
    </>
  );
};
