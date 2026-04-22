import styles from './CircularProgress.module.css';

/**
 * Представляет свойства компонента круглого прогрессбара.
 */
interface CircularProgressProps {
  /** Возвращает значение. */
  readonly value: number;
  /** Возвращает диаметр окружности.. */
  readonly size?: number;
  /** Возвращает ширину окружности. */
  readonly strokeWidth?: number;
  /** Возвращает цвет окружности. */
  readonly color?: string;
  /** Возвращает цвет фона окружности. */
  readonly backgroundColor?: string;
}

/**
 * Представляет компонент круглого прогрессбара.
 */
export const CircularProgress = ({
  value,
  size = 44,
  strokeWidth = 4,
  color = 'var(--base-orange)',
  backgroundColor = 'var(--text-secondary)',
}: CircularProgressProps) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  const progress = Math.min(Math.max(value, 0), 100);
  const offset = circumference - (progress / 100) * circumference;

  return (
    <div
      className={styles.root}
      style={{ width: size, height: size }}
    >
      <svg
        width={size}
        height={size}
      >
        <circle
          stroke={backgroundColor}
          fill="transparent"
          strokeWidth={strokeWidth}
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />

        <circle
          stroke={color}
          fill="transparent"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          r={radius}
          cx={size / 2}
          cy={size / 2}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className={styles.circle}
        />
      </svg>

      <p className={styles.progress}>{Math.round(progress)}%</p>
    </div>
  );
};
