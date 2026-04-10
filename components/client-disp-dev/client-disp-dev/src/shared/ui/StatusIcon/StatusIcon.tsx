import styles from './StatusIcon.module.css';

/** Представляет свойства компонента иконки статуса. */
interface StatusIconProps {
  /** Возвращает цвет иконки. */
  readonly color: string;
}

/**
 * Представляет компонент иконки статуса.
 */
export function StatusIcon(props: StatusIconProps) {
  const { color } = props;

  return (
    <div
      className={styles.root}
      style={{ backgroundColor: color }}
    />
  );
}
