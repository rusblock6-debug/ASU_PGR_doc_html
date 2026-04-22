/** Преобразует unix-миллисекунды в `Date` или `undefined`, если значение невалидно. */
function msToValidDate(ms: number): Date | undefined {
  const d = new Date(ms);
  return Number.isNaN(d.getTime()) ? undefined : d;
}

/** Разбор last_transition: unix (сек/мс), ISO-строка или числовая строка. */
function parseToDate(value: unknown): Date | undefined {
  if (value === null || value === undefined || value === '') {
    return undefined;
  }

  if (typeof value === 'number') {
    return msToValidDate(value < 1e12 ? value * 1000 : value);
  }

  if (typeof value !== 'string') {
    return undefined;
  }

  const trimmed = value.trim();
  if (/^\d+$/.test(trimmed)) {
    const n = Number(trimmed);
    return msToValidDate(n < 1e12 ? n * 1000 : n);
  }

  return msToValidDate(Date.parse(trimmed));
}

/**
 * Преобразует last_transition из API в локальное время ЧЧ:ММ (24ч).
 */
export function formatLastTransitionTime24(value: unknown) {
  const d = parseToDate(value);
  if (!d) {
    return undefined;
  }
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', hour12: false });
}
