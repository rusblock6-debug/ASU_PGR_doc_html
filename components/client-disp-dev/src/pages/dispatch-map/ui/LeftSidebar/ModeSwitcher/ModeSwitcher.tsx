import { FloatingIndicatorGroup } from '@/shared/ui/FloatingIndicator';

import { Mode } from '../../../model/types';
import type { ModeValue } from '../../../model/types';

/** Конфигурация режимов сайдбара. */
const MODES = [
  { value: Mode.VIEW, label: 'Просмотр' },
  { value: Mode.EDIT, label: 'Редактирование' },
  { value: Mode.HISTORY, label: 'История' },
] as const;

/** Представляет свойства компонента переключателя режимов. */
interface ModeSwitcherProps {
  /** Текущий активный режим. */
  readonly activeMode: ModeValue;
  /** Родительский CSS-класс */
  readonly className?: string;
  /** Колбэк при смене режима. */
  readonly onModeChange: (mode: ModeValue) => void;
}

/**
 * Переключатель режимов сайдбара карты с плавающим индикатором.
 */
export function ModeSwitcher({ activeMode, className, onModeChange }: ModeSwitcherProps) {
  return (
    <FloatingIndicatorGroup
      classNames={{ root: className }}
      data={MODES}
      value={activeMode}
      onChange={onModeChange}
    />
  );
}
