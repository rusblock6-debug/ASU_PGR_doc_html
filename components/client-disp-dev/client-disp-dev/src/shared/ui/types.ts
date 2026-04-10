/**
 * Базовый интерфейс для всех input-компонентов.
 * Используется для наследования в TextInput, NumberInput, DateInput и др.
 */
export interface BaseInputOption {
  /**
   * Вариант отображения поля ввода.
   * - `default` — прозрачный фон, соответствует «input_clear» в дизайн-макете
   * - `filled` — заполненный фон, соответствует «input_Filled» в дизайн-макете
   * - `outline` — с обводкой, соответствует «input_Searc_Outline» в дизайн-макете
   * - `combobox-primary` — с обводкой и бэкраундом, соответствует «ComboBox» в дизайн-макете
   * - `unstyled` — без стилей (для кастомизации)
   *
   * @default 'default' соответствует input_clear в дизайн-макете
   */
  readonly variant?: 'default' | 'filled' | 'outline' | 'unstyled' | 'combobox-primary';
  /**
   * Размер поля ввода.
   *
   * @default 'xs'
   */
  readonly inputSize?: 'xs' | 'sm' | 'md' | 'lg' | 'combobox-xs' | 'combobox-sm';
  /**
   * Положение поля ввода и его лейбла.
   *
   * @default 'horizontal'
   */
  readonly labelPosition?: 'horizontal' | 'vertical';
}

/** Базовый интерфейс опции для выпадающих списков. */
export interface SelectOption {
  /** Уникальное значение опции. */
  readonly value: string;
  /** Отображаемое название. */
  readonly label: string;
}

/** Представляет координаты элемента. */
export interface ElementCoordinates {
  /** Возвращает координату по оси Х. */
  readonly x: number;
  /** Возвращает координату по оси У. */
  readonly y: number;
}
