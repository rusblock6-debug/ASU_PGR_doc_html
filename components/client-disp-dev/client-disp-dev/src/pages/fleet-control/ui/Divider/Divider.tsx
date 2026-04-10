/**
 * Представляет свойства компонента разделителя.
 */
interface DividerProps {
  /** Возвращает высоту. */
  readonly height?: number;
  /** Возвращает цвет заливки. */
  readonly color?: string;
}

/**
 * Представляет компонент разделителя.
 */
export function Divider({ height = 2, color = 'var(--bg-widget)' }: DividerProps) {
  return <div style={{ height, background: color }} />;
}
