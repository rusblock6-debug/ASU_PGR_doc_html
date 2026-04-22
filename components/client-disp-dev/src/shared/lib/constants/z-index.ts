/**
 * Возвращает значения z-index. Соответствует css-переменным из файла 'variables.css'.
 */
export const Z_INDEX = {
  DEFAULT: 1,
  SIDEBAR: 10,
  DROPDOWN: 1000,
  STICKY: 1020,
  FIXED: 1030,
  MODAL_BACKDROP: 1040,
  MODAL: 1050,
  POPOVER: 1060,
  TOOLTIP: 1070,
} as const;
