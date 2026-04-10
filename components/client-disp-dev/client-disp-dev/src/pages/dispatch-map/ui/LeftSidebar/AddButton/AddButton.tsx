import PlusIcon from '@/shared/assets/icons/ic-plus.svg?react';
import { AppButton } from '@/shared/ui/AppButton';

/**
 * Представляет свойства компонента кнопки добавления объекта.
 */
interface AddButtonProps {
  /** Возвращает делегат, вызываемый по клику. */
  readonly onClick: () => void;
}

/**
 * Представляет компонент кнопки добавления объекта.
 */
export function AddButton({ onClick }: AddButtonProps) {
  return (
    <AppButton
      variant="primary"
      size="xs"
      onlyIcon
      onClick={onClick}
    >
      <PlusIcon
        width={12}
        height={12}
      />
    </AppButton>
  );
}
