import styles from './Empty.module.css';

export function Empty() {
  return (
    <div>
      <h1 className={styles.heading}>Рабочее пространство пока пустое</h1>
      <p className={styles.text}>сюда можно добавить до 4 страниц для работы</p>
    </div>
  );
}
