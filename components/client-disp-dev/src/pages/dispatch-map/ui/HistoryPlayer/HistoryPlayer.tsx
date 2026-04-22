import { type CSSProperties, useEffect, useRef, useState } from 'react';

import IconCross from '@/shared/assets/icons/ic-cross.svg?react';
import IconFastForward from '@/shared/assets/icons/ic-fast-forward.svg?react';
import IconPause from '@/shared/assets/icons/ic-pause.svg?react';
import IconPlay from '@/shared/assets/icons/ic-play.svg?react';
import IconRepeat from '@/shared/assets/icons/ic-repeat.svg?react';
import { EMPTY_ARRAY, NO_DATA } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { useTimezone } from '@/shared/lib/hooks/useTimezone';
import { useUserLocalStorage } from '@/shared/lib/hooks/useUserLocalStorage';
import { AppButton } from '@/shared/ui/AppButton';
import { Select } from '@/shared/ui/Select';
import { Slider } from '@/shared/ui/Slider';
import { Tooltip } from '@/shared/ui/Tooltip';

import { SIDEBAR_COLLAPSED_KEY, SIDEBAR_EXPANDED_WIDTH } from '../../config/sidebar';
import {
  selectHistoryRangeFilter,
  selectIsPlayHistoryPlayer,
  selectIsVisibleHistoryPlayer,
  selectMapMode,
  selectPlayerCurrentTime,
} from '../../model/selectors';
import { mapActions } from '../../model/slice';
import { Mode } from '../../model/types';

import styles from './HistoryPlayer.module.css';

const SPEED_STEP = 0.25;
const MAX_SPEED = 10;
const DEFAULT_SPEED = 1;
const MAX_STEP = 60;

const SPEED_OPTIONS = Array.from({ length: MAX_SPEED / SPEED_STEP }, (_, i) => {
  const value = (i + 1) * SPEED_STEP;
  return {
    label: `${value}x`,
    value: String(value),
  };
});

/**
 * Представляет компонент плеера истории оборудования.
 */
export function HistoryPlayer() {
  const dispatch = useAppDispatch();
  const historyRangeFilter = useAppSelector(selectHistoryRangeFilter);
  const mode = useAppSelector(selectMapMode);
  const isVisibleHistoryPlayer = useAppSelector(selectIsVisibleHistoryPlayer);
  const isPlayHistoryPlayer = useAppSelector(selectIsPlayHistoryPlayer);
  const playerCurrentTime = useAppSelector(selectPlayerCurrentTime);

  const playerCurrentTimeRef = useRef(playerCurrentTime);

  useEffect(() => {
    playerCurrentTimeRef.current = playerCurrentTime;
  }, [playerCurrentTime]);

  const stepCountRef = useRef(0);
  const stepResetTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [currentStep, setCurrentStep] = useState(10);

  const isHistoryMode = mode === Mode.HISTORY;

  const tz = useTimezone();
  const [isLeftCollapsed] = useUserLocalStorage(SIDEBAR_COLLAPSED_KEY, false);

  const fromTime = historyRangeFilter ? new Date(historyRangeFilter.from).getTime() : null;

  const toTime = historyRangeFilter ? new Date(historyRangeFilter.to).getTime() : null;

  const interval = useRef<ReturnType<typeof setInterval> | null>(null);

  const [speed, setSpeed] = useState(DEFAULT_SPEED);

  const style = {
    '--sidebar-offset': isLeftCollapsed ? undefined : `${SIDEBAR_EXPANDED_WIDTH + 8}px`,
  } as CSSProperties;

  const start = (playSpeed: number) => {
    if (!fromTime || !toTime) return;

    if (interval.current) {
      clearInterval(interval.current);
      interval.current = null;
    }

    interval.current = setInterval(() => {
      const current = playerCurrentTimeRef.current;

      if (!hasValue(current)) {
        return;
      }

      const newTime = current + 1000;

      if (newTime >= toTime) {
        stop();
        dispatch(mapActions.setPlayerCurrentTime(toTime));
        return;
      }

      dispatch(mapActions.setPlayerCurrentTime(newTime));
    }, 1000 / playSpeed);

    dispatch(mapActions.togglePlayHistoryPlayer(true));
  };

  const stop = () => {
    if (interval.current) {
      clearInterval(interval.current);
      interval.current = null;
    }

    dispatch(mapActions.togglePlayHistoryPlayer(false));
  };

  const resetStepProgression = () => {
    stepCountRef.current = 0;
    setCurrentStep(10);
    if (stepResetTimeoutRef.current) {
      clearTimeout(stepResetTimeoutRef.current);
      stepResetTimeoutRef.current = null;
    }
  };

  const step = (direction: 'back' | 'forward') => {
    if (!fromTime || !toTime || !hasValue(playerCurrentTime)) return;

    stepCountRef.current += 1;

    const step = Math.min(10 * stepCountRef.current, MAX_STEP);
    const delta = (direction === 'back' ? -step : step) * 1000;
    let newTime = playerCurrentTime + delta;

    newTime = Math.min(Math.max(newTime, fromTime), toTime);

    dispatch(mapActions.setPlayerCurrentTime(newTime));
    setCurrentStep(step);

    if (stepResetTimeoutRef.current) {
      clearTimeout(stepResetTimeoutRef.current);
      stepResetTimeoutRef.current = null;
    }

    stepResetTimeoutRef.current = setTimeout(resetStepProgression, 800);
  };

  const rewind = () => step('back');
  const forward = () => step('forward');

  const changeSpeed = (value: string | null) => {
    if (hasValue(value)) {
      const newSpeed = Number(value);
      setSpeed(newSpeed);

      if (isPlayHistoryPlayer) {
        start(newSpeed);
      }
    }
  };

  const repeat = () => {
    if (!fromTime) return;

    dispatch(mapActions.setPlayerCurrentTime(fromTime));
    start(speed);
  };

  const close = () => {
    dispatch(mapActions.toggleVisibleHistoryPlayer(false));
    dispatch(mapActions.setPlayerCurrentTime(null));
    dispatch(mapActions.togglePlayHistoryPlayer(false));
    dispatch(mapActions.setVehicleHistoryMarks(EMPTY_ARRAY));

    if (interval.current) {
      clearInterval(interval.current);
      interval.current = null;
    }
  };

  useEffect(() => {
    if (!isHistoryMode && interval.current) {
      clearInterval(interval.current);
      interval.current = null;
    }
  }, [isHistoryMode]);

  useEffect(() => {
    return () => {
      if (interval.current) {
        clearInterval(interval.current);
      }
    };
  }, []);

  const showRepeatButton = hasValue(playerCurrentTime) && hasValue(toTime) && playerCurrentTime >= toTime;

  if (!isVisibleHistoryPlayer || !isHistoryMode) {
    return null;
  }

  return (
    <div
      className={styles.root}
      style={style}
    >
      <div className={styles.toolbar_container}>
        <div className={styles.toolbar_buttons_container}>
          <Tooltip label={`-${currentStep} сек.`}>
            <AppButton
              size="s"
              onlyIcon
              variant="clear"
              className={styles.rewind_icon}
              onClick={rewind}
            >
              <IconFastForward />
            </AppButton>
          </Tooltip>
          <AppButton
            size="s"
            onlyIcon
            onClick={() => {
              if (!isPlayHistoryPlayer) {
                start(speed);
              } else {
                stop();
              }
            }}
          >
            {isPlayHistoryPlayer ? <IconPause className={styles.pause_icon} /> : <IconPlay />}
          </AppButton>
          <Tooltip label={`+${currentStep} сек.`}>
            <AppButton
              size="s"
              onlyIcon
              variant="clear"
              onClick={forward}
            >
              <IconFastForward />
            </AppButton>
          </Tooltip>
        </div>
        <Select
          className={styles.speed_select}
          styles={{ root: { ['--label-width']: 'auto', ['--column-gap']: '2px' } }}
          label="Скорость"
          name="Скорость"
          labelPosition="horizontal"
          data={SPEED_OPTIONS}
          value={String(speed)}
          onChange={changeSpeed}
        />
      </div>
      <div className={styles.player_container}>
        <Slider
          min={historyRangeFilter ? new Date(historyRangeFilter.from).getTime() : undefined}
          max={historyRangeFilter ? new Date(historyRangeFilter.to).getTime() : undefined}
          classNames={{
            thumb: styles.thumb,
            track: styles.track,
          }}
          color="var(--base-orange)"
          size="xs"
          thumbSize={12}
          label={(value) => tz.format(new Date(value), 'HH:mm:ss dd.MM.yyyy')}
          value={playerCurrentTime ?? (historyRangeFilter ? new Date(historyRangeFilter.from).getTime() : undefined)}
          onChange={(value) => {
            dispatch(mapActions.setPlayerCurrentTime(Math.round(value / 1000) * 1000));
          }}
        />
        <div className={styles.dates_container}>
          <p>
            <span className={styles.date_label}>Начало</span>{' '}
            <span className={styles.date_value}>
              {historyRangeFilter ? tz.format(historyRangeFilter.from, 'HH:mm dd.MM.yyyy') : NO_DATA.DASH}
            </span>
          </p>
          <p>
            <span className={styles.date_label}>Конец</span>{' '}
            <span className={styles.date_value}>
              {historyRangeFilter ? tz.format(historyRangeFilter.to, 'HH:mm dd.MM.yyyy') : NO_DATA.DASH}
            </span>
          </p>
        </div>
      </div>
      <div className={styles.action_buttons_container}>
        <Tooltip label="Закрыть">
          <AppButton
            size="xxs"
            onlyIcon
            variant="clear"
            onClick={close}
          >
            <IconCross className={styles.cross_icon} />
          </AppButton>
        </Tooltip>

        {showRepeatButton && (
          <Tooltip label="Запустить заново">
            <AppButton
              size="xxs"
              onlyIcon
              variant="clear"
              onClick={repeat}
            >
              <IconRepeat />
            </AppButton>
          </Tooltip>
        )}
      </div>
    </div>
  );
}
