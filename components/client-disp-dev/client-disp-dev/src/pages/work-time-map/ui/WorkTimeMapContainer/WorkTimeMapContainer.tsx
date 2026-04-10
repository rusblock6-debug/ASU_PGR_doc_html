import { LoadingSpinner } from '@/shared/ui/LoadingSpinner';

import { useWorkTimeMapPageContext } from '../../model/WorkTimeMapPageContext';
import { WorkTimeMap } from '../WorkTimeMap';

/**
 * Представляет компонент контейнера для компонента карты рабочего времени.
 */
export function WorkTimeMapContainer() {
  const { shiftDefinitions } = useWorkTimeMapPageContext();

  return shiftDefinitions.length > 0 ? <WorkTimeMap /> : <LoadingSpinner />;
}
