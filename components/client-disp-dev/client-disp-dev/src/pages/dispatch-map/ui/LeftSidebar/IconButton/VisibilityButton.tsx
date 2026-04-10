import EyePartialIcon from '@/shared/assets/icons/ic-eye-half-closed.svg?react';
import EyeOffIcon from '@/shared/assets/icons/ic-eye-off.svg?react';
import EyeIcon from '@/shared/assets/icons/ic-eye.svg?react';

import { GroupVisibility, type GroupVisibilityValue } from '../../../model/lib/compute-group-visibility';

import { IconButton } from './IconButton';

/**
 * Представляет свойства компонента {@link VisibilityButton}.
 */
interface VisibilityToggleProps {
  /** Текущее состояние видимости группы. */
  readonly visibility: GroupVisibilityValue;
  /** Колбэк переключения видимости. */
  readonly onToggle: () => void;
}

/**
 * Кнопка-переключатель видимости с иконкой глаза.
 */
export function VisibilityButton({ visibility, onToggle }: VisibilityToggleProps) {
  const isHidden = visibility === GroupVisibility.HIDDEN;
  const isPartial = visibility === GroupVisibility.PARTIAL;
  const isVisible = visibility === GroupVisibility.VISIBLE;

  return (
    <IconButton
      title={isVisible ? 'Скрыть' : 'Показать'}
      onClick={onToggle}
    >
      {isHidden && <EyeOffIcon />}
      {isVisible && <EyeIcon />}
      {isPartial && <EyePartialIcon />}
    </IconButton>
  );
}
