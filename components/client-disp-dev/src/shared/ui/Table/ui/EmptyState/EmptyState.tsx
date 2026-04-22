import styles from './EmptyState.module.css';

interface EmptyStateProps {
  readonly columnsCount: number;
}

export function EmptyState({ columnsCount }: EmptyStateProps) {
  return (
    <tbody className={styles.empty_tbody}>
      <tr>
        <td
          colSpan={columnsCount}
          className={styles.empty_cell}
        >
          <div className={styles.empty_content}>Нет данных для отображения</div>
        </td>
      </tr>
    </tbody>
  );
}
