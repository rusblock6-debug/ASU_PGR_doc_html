import type { PropsWithChildren } from 'react';

import { useGroundPointerContext } from '../GroundPointerProvider';

import styles from './StatusBar.module.css';

/**
 * Панель состояния карты: координаты мыши, масштаб и компас.
 */
export function StatusBar({ children }: Readonly<PropsWithChildren>) {
  const { xRef, yRef } = useGroundPointerContext();

  return (
    <div className={styles.root}>
      <div className={styles.item}>
        <span className={styles.text}>
          X: <span ref={xRef}>0</span>
        </span>
        <span className={styles.text}>
          Y: <span ref={yRef}>0</span>
        </span>
      </div>

      <div className={styles.item}>
        <span className={styles.text}>1:1000</span>
      </div>

      {children}
    </div>
  );
}
