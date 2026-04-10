import EyeOffIcon from '@/shared/assets/icons/ic-eye-off.svg?react';
import EyeIcon from '@/shared/assets/icons/ic-eye.svg?react';
import { AppButton } from '@/shared/ui/AppButton';

import styles from './LayerToggle.module.css';

/**
 * Представляет свойства компонента {@link LayerToggle}.
 */
interface LayerToggleProps {
  /** Отображаемое название слоя. */
  readonly label: string;
  /** Видимость слоя на карте. */
  readonly visible: boolean;
  /** Колбэк при переключении видимости слоя. */
  readonly onToggle: () => void;
}

/**
 * Кнопка переключения видимости слоя карты.
 */
export function LayerToggle({ label, visible, onToggle }: LayerToggleProps) {
  return (
    <div className={styles.layer}>
      <AppButton
        className={styles.layer_button}
        size="xs"
        variant="clear"
        onClick={onToggle}
      >
        <span className={styles.layer_button_inner}>
          {visible ? (
            <EyeIcon className={styles.layer_button_icon} />
          ) : (
            <EyeOffIcon className={styles.layer_button_icon} />
          )}
          <span className={styles.layer_button_text}>{label}</span>
        </span>
      </AppButton>
    </div>
  );
}
