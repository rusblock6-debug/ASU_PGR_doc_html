import { UnstyledButton } from '@mantine/core';

import GpsIcon from '@/shared/assets/icons/ic-gps-fixed-light.svg?react';

import { useMapCameraContext } from '../MapCameraProvider';

import styles from './Compass.module.css';

/** Стороны света для отображения на компасе. */
const DIRECTIONS = [
  { position: 'north', label: 'С' },
  { position: 'east', label: 'В' },
  { position: 'south', label: 'Ю' },
  { position: 'west', label: 'З' },
] as const;

/**
 * Кнопка со сторонами света, вращающаяся в соответствии с положением камеры.
 */
export function Compass() {
  const { compassRef, resetCamera } = useMapCameraContext();

  return (
    <div className={styles.wrapper}>
      <UnstyledButton
        ref={compassRef}
        className={styles.root}
        title="Вернуть к начальной позиции"
        onClick={resetCamera}
      >
        {DIRECTIONS.map(({ position, label }) => (
          <span
            key={position}
            className={styles.label}
            data-position={position}
          >
            {label}
          </span>
        ))}
        <GpsIcon className={styles.icon} />
      </UnstyledButton>
    </div>
  );
}
