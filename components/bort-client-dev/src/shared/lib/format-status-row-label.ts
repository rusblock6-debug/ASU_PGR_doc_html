/** Человекочитаемая подпись строки статуса из enterprise `/api/statuses`. */
export function formatStatusRowLabel(status: Readonly<Record<string, unknown>>) {
  const displayName = status.display_name;
  if (typeof displayName === 'string' && displayName.trim()) {
    return displayName.trim();
  }
  const idRaw = status.id;
  const idStr = typeof idRaw === 'string' || typeof idRaw === 'number' ? String(idRaw) : '';
  const raw =
    (typeof status.name === 'string' && status.name) ||
    (typeof status.label === 'string' && status.label) ||
    (typeof status.title === 'string' && status.title) ||
    (typeof status.description === 'string' && status.description) ||
    (typeof status.code === 'string' && status.code) ||
    idStr;
  return raw.toLocaleUpperCase('ru-RU');
}
