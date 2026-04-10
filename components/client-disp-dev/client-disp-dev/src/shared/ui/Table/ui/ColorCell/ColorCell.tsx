import styles from './ColorCell.module.css';

/**
 * Представляет свойства для компонента {@link ColorCell}.
 */
interface ColorCellProps {
  /**
   * Возвращает цвет.
   */
  readonly color: string;
}

/**
 * Представляет компонент ячейки отображающей цвет.
 */
export function ColorCell(props: ColorCellProps) {
  return (
    <div
      style={{ background: props.color }}
      className={styles.root}
    />
  );
}
