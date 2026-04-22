/** Плейсхолдер для поля MAC-адреса. */
export const MAC_ADDRESS_PLACEHOLDER = 'XX:XX:XX:XX:XX:XX';

/** Regex для валидации MAC-адреса в формате XX:XX:XX:XX:XX:XX. */
export const MAC_ADDRESS_REGEX = /^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/;

/** Regex для извлечения hex-символов. */
const HEX_ONLY_REGEX = /[^0-9A-Fa-f]/g;

/**
 * Форматирует строку как MAC-адрес (XX:XX:XX:XX:XX:XX).
 * Удаляет все символы кроме hex, приводит к верхнему регистру и добавляет разделители.
 */
export function formatMacAddress(value: string) {
  const hex = value.replace(HEX_ONLY_REGEX, '').toUpperCase().slice(0, 12);
  return hex.match(/.{1,2}/g)?.join(':') ?? hex;
}
