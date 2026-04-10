import { FloatingIndicatorGroup } from '@/shared/ui/FloatingIndicator';

import { HorizonFilter, type HorizonFilterValue } from '../../../../model/types';

/** Конфигурация вариантов горизонта. */
const MODES = [
  { value: HorizonFilter.CURRENT_HORIZON, label: 'На горизонте' },
  { value: HorizonFilter.ALL, label: 'Все' },
] as const;

/** Представляет свойства компонента переключателя горизонта. */
interface HorizonSwitcherProps {
  /** Текущий горизонт. */
  readonly activeHorizon: HorizonFilterValue;
  /** Колбэк при смене горизонта. */
  readonly onHorizonChange: (horizon: HorizonFilterValue) => void;
}

/**
 * Переключатель режимов сайдбара карты с плавающим индикатором.
 */
export function HorizonSwitcher({ activeHorizon, onHorizonChange }: HorizonSwitcherProps) {
  return (
    <FloatingIndicatorGroup
      data={MODES}
      value={activeHorizon}
      onChange={onHorizonChange}
    />
  );
}
