import type { CSSProperties, PropsWithChildren } from 'react';
import { useState } from 'react';

import type { SubstrateResponse } from '@/shared/api/endpoints/substrates';
import { useUpdateSubstrateMutation } from '@/shared/api/endpoints/substrates';
import ConfirmIcon from '@/shared/assets/icons/ic-confirm.svg?react';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { AppButton } from '@/shared/ui/AppButton';
import { Popover } from '@/shared/ui/Popover';
import { Slider } from '@/shared/ui/Slider';
import { toast } from '@/shared/ui/Toast';

import { mapActions } from '../../../../../model/slice';
import { IconButton } from '../../../IconButton';

import styles from './BrightnessPopover.module.css';

/**
 * Пропсы компонента BrightnessPopover.
 */
interface BrightnessPopoverProps {
  /** Подложка. */
  readonly substrate: SubstrateResponse;
}

/**
 * Поповер для управления яркостью конкретной подложки.
 * Держит локальный драфт значения, обновляет предпросмотр в Redux и сохраняет значение через RTK-мутаторы.
 */
export function BrightnessPopover({ substrate, children }: PropsWithChildren<BrightnessPopoverProps>) {
  const dispatch = useAppDispatch();

  const [opened, setOpened] = useState(false);
  const [draft, setDraft] = useState<number>(50);
  const [isSaving, setIsSaving] = useState(false);
  const [updateSubstrate] = useUpdateSubstrateMutation();

  const handleOpen = () => {
    const initialOpacity = Number.isFinite(substrate.opacity) ? substrate.opacity : 50;

    setDraft(initialOpacity);
    setOpened(true);
    dispatch(mapActions.setBackgroundPreviewOpacity(initialOpacity));
  };

  const handleClose = () => {
    setOpened(false);
    dispatch(mapActions.setBackgroundPreviewOpacity(null));
  };

  const handleChange = (value: number) => {
    if (Number.isNaN(value)) return;

    const clamped = Math.min(100, Math.max(0, value));

    setDraft(clamped);
  };

  const handleChangeEnd = (value: number) => {
    if (Number.isNaN(value)) return;

    const clamped = Math.min(100, Math.max(0, value));

    dispatch(mapActions.setBackgroundPreviewOpacity(clamped));
  };

  const handleApply = async () => {
    const opacity = Math.round(draft);

    setIsSaving(true);
    setOpened(false);

    try {
      await updateSubstrate({
        id: substrate.id,
        body: { opacity },
      }).unwrap();
      toast.success({ message: 'Яркость подложки обновлена' });
    } catch {
      toast.error({ message: 'Не удалось обновить яркость подложки' });
    } finally {
      dispatch(mapActions.setBackgroundPreviewOpacity(null));
      setIsSaving(false);
    }
  };

  if (isSaving) {
    return <span className={styles.spinner_inline} />;
  }

  return (
    <Popover
      opened={opened}
      onChange={(nextOpened) => {
        if (!nextOpened) handleClose();
      }}
      position="bottom-start"
      offset={4}
      withinPortal
    >
      <Popover.Target>
        <IconButton
          title="Настроить яркость подложки"
          aria-label="Настроить яркость подложки"
          onClick={handleOpen}
        >
          {children}
        </IconButton>
      </Popover.Target>

      <Popover.Dropdown className={styles.brightness_dropdown}>
        <div className={styles.brightness_popover}>
          <div className={styles.brightness_title}>Яркость подложки</div>

          <div className={styles.brightness_body}>
            <div className={styles.brightness_slider_col}>
              <Slider
                value={draft}
                onChange={handleChange}
                onChangeEnd={handleChangeEnd}
                min={0}
                max={100}
                step={1}
                marks={[{ value: 20 }, { value: 50 }, { value: 80 }]}
                style={{ '--slider-color': 'var(--primary)' } as CSSProperties}
                classNames={{ thumb: styles.brightness_slider_thumb, mark: styles.brightness_slider_mark }}
              />
              <div className={styles.brightness_marks}>
                <span className={styles.brightness_mark}>20%</span>
                <span className={styles.brightness_mark}>50%</span>
                <span className={styles.brightness_mark}>80%</span>
              </div>
            </div>

            <span className={styles.brightness_value}>{Math.round(draft)}%</span>

            <AppButton
              className={styles.brightness_apply_button}
              variant="primary"
              size="xs"
              onlyIcon
              onClick={handleApply}
            >
              <ConfirmIcon />
            </AppButton>
          </div>
        </div>
      </Popover.Dropdown>
    </Popover>
  );
}
