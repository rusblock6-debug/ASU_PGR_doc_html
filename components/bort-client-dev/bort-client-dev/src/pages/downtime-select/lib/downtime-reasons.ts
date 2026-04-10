/** Элемент списка причин простоя для экрана выбора. */
export interface DowntimeReasonItem {
  readonly id: string;
  /** Подпись на кнопке (верхний регистр под kiosk). */
  readonly label: string;
}

/**
 * Фиксированный перечень причин простоя (две страницы по сетке 2×4: 7+«след.» и 6).
 */
export const DOWNTIME_REASONS: readonly DowntimeReasonItem[] = [
  { id: 'work_delays', label: 'РАБОЧИЕ ЗАДЕРЖКИ' },
  { id: 'energy_downtime', label: 'ЭНЕРГЕТИЧЕСКИЙ ПРОСТОЙ' },
  { id: 'auxiliary_works', label: 'ВСПОМОГАТЕЛЬНЫЕ РАБОТЫ' },
  { id: 'eco_climatic', label: 'ЭКОЛОГО-КЛИМАТИЧЕСКИЕ ПРОСТОИ' },
  { id: 'regulated_breaks', label: 'РЕГЛАМЕНТИРУЕМЫЕ ПЕРЕРЫВЫ' },
  { id: 'reserve_unplanned', label: 'РЕЗЕРВ (НЕ ПЛАНИРУЕМЫЙ)' },
  { id: 'technological', label: 'ТЕХНОЛОГИЧЕСКИЕ ПРОСТОИ' },
  { id: 'gravel_transport', label: 'ПЕРЕВОЗКА ЩЕБНЯ' },
  { id: 'snow_transport', label: 'ПЕРЕВОЗКА СНЕГА' },
  { id: 'utility_quarries', label: 'РАБОТА НА ХОЗ КАРЬЕРАХ' },
  { id: 'tailings', label: 'РАБОТА НА ХВОСТАХ' },
  { id: 'intra_warehouse', label: 'ПЕРЕВОЗКА ВНУТРИСКЛАД' },
  { id: 'new_equipment_tests', label: 'ИСПЫТАНИЯ НОВОГО ОБОРУДОВАНИЯ' },
];
