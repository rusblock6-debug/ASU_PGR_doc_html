import styles from './LoadingSpinner.module.css';

/**
 * Представляет компонент индикатора загрузки.
 */
export function LoadingSpinner() {
  return (
    <div className={styles.spinner_container}>
      <div className={styles.spinner} />
      <span className={styles.loading_text}>Загрузка...</span>
    </div>
  );
}
