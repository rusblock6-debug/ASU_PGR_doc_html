import { useEffect, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';

import { useSetVehicleStateTransitionMutation } from '@/shared/api';
import { cn } from '@/shared/lib/classnames-utils';
import { savePrevStatusBeforeIdle } from '@/shared/lib/downtime-session';
import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';
import { selectVehicleState } from '@/shared/lib/vehicle-events';
import {
  findChainIndexByStreamState,
  normStateCode,
  STANDARD_STATUS_CHAIN,
  STANDARD_STATUS_CHAIN_LEN,
} from '@/shared/lib/vehicle-status-chain';
import { getRouteDowntimeSelect } from '@/shared/routes/router';

import styles from './VehicleStatusPage.module.css';

const KIOSK_FORWARD_ID = 'vehicle-status-forward';
const KIOSK_DOWNTIME_ID = 'vehicle-status-downtime';

/**
 * Управление статусом борта: цепочка состояний и действия «вперёд» / «простой».
 */
export const VehicleStatusPage = () => {
  const navigate = useNavigate();
  const streamStateStatus = useSelector(selectVehicleState);

  const { setItemIds, setOnConfirm, selectedId } = useKioskNavigation();

  const [listSelectedIndex, setListSelectedIndex] = useState(0);
  const [setTransition, { isLoading: isTransitioning }] = useSetVehicleStateTransitionMutation();

  const rowRefs = useRef<(HTMLDivElement | null)[]>([]);

  const completedThroughIndex = findChainIndexByStreamState(streamStateStatus ?? undefined);

  const nextForwardState =
    listSelectedIndex < 0 || listSelectedIndex >= STANDARD_STATUS_CHAIN_LEN - 1
      ? null
      : STANDARD_STATUS_CHAIN[listSelectedIndex + 1].en;

  const canGoForward = Boolean(nextForwardState) && !isTransitioning;

  const resolveCurrentStateCodeForStorage = () => {
    if (completedThroughIndex >= 0) {
      return STANDARD_STATUS_CHAIN[completedThroughIndex].en;
    }
    const n = normStateCode(streamStateStatus ?? undefined);
    if (n) {
      return n;
    }
    return STANDARD_STATUS_CHAIN[0].en;
  };

  const goToDowntimeSelect = () => {
    savePrevStatusBeforeIdle(resolveCurrentStateCodeForStorage());
    void navigate(getRouteDowntimeSelect());
  };

  const handleForward = () => {
    if (!nextForwardState) {
      return;
    }
    void setTransition({ new_state: nextForwardState, reason: 'manual', comment: '' })
      .unwrap()
      .then(() => {
        setListSelectedIndex((prev) => Math.min(prev + 1, STANDARD_STATUS_CHAIN_LEN - 1));
      });
  };

  const handleForwardRef = useRef(handleForward);
  const goToDowntimeSelectRef = useRef(goToDowntimeSelect);
  handleForwardRef.current = handleForward;
  goToDowntimeSelectRef.current = goToDowntimeSelect;

  useEffect(() => {
    if (completedThroughIndex >= 0) {
      setListSelectedIndex(completedThroughIndex);
    }
  }, [completedThroughIndex]);

  useEffect(() => {
    setItemIds([KIOSK_FORWARD_ID, KIOSK_DOWNTIME_ID]);
  }, [setItemIds]);

  useEffect(() => {
    setOnConfirm(() => {
      if (selectedId === KIOSK_FORWARD_ID) {
        handleForwardRef.current();
        return;
      }
      if (selectedId === KIOSK_DOWNTIME_ID) {
        goToDowntimeSelectRef.current();
      }
    });
    return () => {
      setOnConfirm(null);
    };
  }, [selectedId, setOnConfirm]);

  useEffect(() => {
    rowRefs.current[listSelectedIndex]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [listSelectedIndex]);

  return (
    <div className={styles.page}>
      <div className={styles.controls}>
        <button
          type="button"
          className={cn(styles.action_btn, selectedId === KIOSK_FORWARD_ID && styles.action_btn_selected)}
          aria-label="Статус вперёд"
          disabled={!canGoForward}
          onClick={handleForward}
        >
          <span
            className={styles.action_btn_forward_icon}
            aria-hidden
          />
          СТАТУС ВПЕРЕД
        </button>
        <button
          type="button"
          className={cn(
            styles.action_btn,
            styles.action_btn_downtime,
            selectedId === KIOSK_DOWNTIME_ID && styles.action_btn_selected,
          )}
          aria-label="Простои"
          disabled={isTransitioning}
          onClick={goToDowntimeSelect}
        >
          ПРОСТОИ
          <span
            className={styles.downtime_icon}
            aria-hidden
          />
        </button>
      </div>
      <div className={styles.list_wrap}>
        <div
          className={styles.list}
          role="list"
          aria-label="Цепочка статусов"
        >
          {STANDARD_STATUS_CHAIN.map((item, index) => {
            const isCompleted = completedThroughIndex >= 0 && index <= completedThroughIndex;
            const isCurrent = index === listSelectedIndex;
            const currentLabelWords = item.ru.split(' ');
            const hasForcedSecondLine = isCurrent && currentLabelWords.length >= 3;
            const currentLineOne = hasForcedSecondLine ? currentLabelWords.slice(0, -1).join(' ') : item.ru;
            const currentLineTwo = hasForcedSecondLine ? currentLabelWords[currentLabelWords.length - 1] : '';

            return (
              <div
                key={item.code}
                ref={(el) => {
                  rowRefs.current[index] = el;
                }}
                role="listitem"
                className={cn(
                  styles.row,
                  (isCompleted || isCurrent) && styles.row_completed_stripe,
                  isCurrent && styles.row_current,
                )}
              >
                <div className={styles.row_text}>
                  <span className={cn(styles.row_primary, isCompleted && styles.row_primary_completed)}>
                    {hasForcedSecondLine ? (
                      <>
                        <span className={styles.row_primary_line}>{currentLineOne}</span>
                        <span className={styles.row_primary_line_secondary}>{currentLineTwo}</span>
                      </>
                    ) : (
                      item.ru
                    )}
                  </span>
                </div>
                <span
                  className={styles.row_time}
                  aria-hidden
                />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
