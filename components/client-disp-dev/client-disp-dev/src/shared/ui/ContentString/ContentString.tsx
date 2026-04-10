import { nanoid } from '@reduxjs/toolkit';
import type { ReactNode } from 'react';

import { cn } from '@/shared/lib/classnames-utils';
import { NO_DATA } from '@/shared/lib/constants';

import { Skeleton } from '../Skeleton';

import styles from './ContentString.module.css';

/** Представляет свойства компонента строки контента для информационных окон. */
interface ContentStringProps {
  /** Возвращает заголовок. */
  readonly title: string;
  /** Возвращает список значений. */
  readonly values: string[];
  /** Возвращает элемент расположенный после списка значений. */
  readonly afterElement?: ReactNode;
  /** Возвращает состояние загрузки. */
  readonly isLoading?: boolean;
  /** Возвращает селектор для строки с информацией. */
  readonly stringInfoClassName?: string;
}

/**
 * Представляет компонент строки контента для информационных окон.
 */
export function ContentString(props: ContentStringProps) {
  const { title, values, afterElement, isLoading, stringInfoClassName } = props;

  return (
    <div className={styles.content_string}>
      <p className={styles.string_title}>{title}</p>
      <div className={styles.string_info_container}>
        {isLoading ? (
          <Skeleton />
        ) : (
          <>
            {values.map((item) => (
              <p
                key={item === NO_DATA.DASH ? nanoid() : item}
                className={cn(styles.string_info, stringInfoClassName)}
              >
                {item}
              </p>
            ))}
            {afterElement}
          </>
        )}
      </div>
    </div>
  );
}
