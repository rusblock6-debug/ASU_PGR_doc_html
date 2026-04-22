import { useNavigate } from 'react-router-dom';

import { KioskBackButton } from '@/shared/ui/KioskBackButton';

import { ConfirmButton } from '../ConfirmButton';

/**
 * Левая зона kiosk-управления: «назад» вверху (браузерная история) и подтверждение внизу.
 */
export const KioskLeftSidebar = () => {
  const navigate = useNavigate();

  return (
    <>
      <KioskBackButton onClick={() => void navigate(-1)} />
      <ConfirmButton />
    </>
  );
};
