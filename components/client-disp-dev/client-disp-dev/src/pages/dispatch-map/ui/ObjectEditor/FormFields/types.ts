/**
 * Представляет свойства компонента поля ввода формы.
 */
export interface FormFieldProps {
  /** Возвращает наименование. */
  readonly name: string;
  /** Возвращает заголовок */
  readonly label: string;
  /** Возвращает признак, что поле обязательное. */
  readonly required?: boolean;
  /** Возвращает признак, что поле доступно только для чтения. */
  readonly readOnly?: boolean;
  /** Возвращает признак, что поле заблокировано для редактирования. */
  readonly disabled?: boolean;
}
