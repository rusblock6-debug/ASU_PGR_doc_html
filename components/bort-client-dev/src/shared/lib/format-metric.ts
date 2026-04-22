/**
 * Округляет число до двух знаков после запятой и возвращает строку.
 */
export const formatMetric = (value: number) => {
  const rounded = Math.round(value * 100) / 100;
  return String(rounded);
};
