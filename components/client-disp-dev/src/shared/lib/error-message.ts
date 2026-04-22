/**
 * Извлекает сообщение об ошибке из различных форматов.
 *
 * @param error Ошибка любого типа.
 * @param fallbackMessage Сообщение по умолчанию, если не удалось извлечь.
 */
export function getErrorMessage(error: unknown, fallbackMessage = 'Ошибка сервера') {
  const detail = (error as { data?: { detail?: unknown } })?.data?.detail;

  // API ошибка с detail-строкой
  if (typeof detail === 'string') return detail;

  // Pydantic validation error: detail — массив с msg
  if (Array.isArray(detail) && detail.length > 0) {
    const messages = detail.map((item) => (item as { msg?: string }).msg).filter(Boolean);
    if (messages.length > 0) return messages.join('; ');
  }

  // Стандартная Error
  if (error instanceof Error) return error.message;

  // Строка
  if (typeof error === 'string') return error;

  return fallbackMessage;
}
