/**
 * Фиксированный порядок статусов (совпадает с state machine).
 * `en` — код для POST /state/transition `new_state`.
 */
export const STANDARD_STATUS_CHAIN = [
  { code: 'moving_empty', ru: 'Движение порожним', en: 'moving_empty' },
  { code: 'stopped_empty', ru: 'Остановка порожним', en: 'stopped_empty' },
  { code: 'loading', ru: 'Погрузка', en: 'loading' },
  { code: 'moving_loaded', ru: 'Движение с грузом', en: 'moving_loaded' },
  { code: 'stopped_loaded', ru: 'Остановка с грузом', en: 'stopped_loaded' },
  { code: 'unloading', ru: 'Разгрузка', en: 'unloading' },
] as const;

export const STANDARD_STATUS_CHAIN_LEN = STANDARD_STATUS_CHAIN.length;

export const normStateCode = (s: string | undefined) => s?.trim().toLowerCase().replaceAll('-', '_') ?? '';

/** Индекс текущего шага в цепочке по коду из стрима/API. */
export function findChainIndexByStreamState(streamState: string | undefined) {
  if (!streamState) {
    return -1;
  }
  const n = normStateCode(streamState);
  return STANDARD_STATUS_CHAIN.findIndex((item) => item.code === n);
}

/** Русская подпись статуса по коду (если есть в цепочке). */
export function getRuLabelForStateCode(code: string) {
  const n = normStateCode(code);
  return STANDARD_STATUS_CHAIN.find((item) => item.code === n)?.ru;
}
