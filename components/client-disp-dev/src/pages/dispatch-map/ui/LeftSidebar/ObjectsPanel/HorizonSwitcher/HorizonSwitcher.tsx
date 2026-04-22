import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { FloatingIndicatorGroup } from '@/shared/ui/FloatingIndicator';

import { selectHorizonFilter } from '../../../../model/selectors';
import { mapActions } from '../../../../model/slice';
import { HorizonFilter, type HorizonFilterValue } from '../../../../model/types';

/** Конфигурация вариантов горизонта. */
const MODES = [
  { value: HorizonFilter.CURRENT_HORIZON, label: 'На горизонте' },
  { value: HorizonFilter.ALL, label: 'Все' },
] as const;

/**
 * Переключатель режимов сайдбара карты с плавающим индикатором.
 */
export function HorizonSwitcher() {
  const dispatch = useAppDispatch();
  const activeHorizon = useAppSelector(selectHorizonFilter);

  const handleChange = (horizon: HorizonFilterValue) => {
    dispatch(mapActions.setObjectFilter(horizon));
  };

  return (
    <FloatingIndicatorGroup
      data={MODES}
      value={activeHorizon}
      onChange={handleChange}
    />
  );
}
