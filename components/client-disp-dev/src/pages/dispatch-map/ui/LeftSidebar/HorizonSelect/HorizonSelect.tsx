import { useEffect } from 'react';

import { useLazyGetHorizonGraphQuery } from '@/shared/api/endpoints/horizons';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { Select } from '@/shared/ui/Select';

import { useExitGraphEdit } from '../../../lib/hooks/useExitGraphEdit';
import { useMapPlaces } from '../../../lib/hooks/useMapPlaces';
import { selectSelectedHorizonId } from '../../../model/selectors';
import { mapActions } from '../../../model/slice';

import styles from './HorizonSelect.module.css';

/**
 * Селектор горизонта в шапке сайдбара.
 *
 * Загружает список горизонтов, инициализирует выбор из localStorage / первого элемента,
 * и синхронизирует значение с Redux.
 */
export function HorizonSelect() {
  const dispatch = useAppDispatch();
  const selectedHorizonId = useAppSelector(selectSelectedHorizonId);
  const exitGraphEdit = useExitGraphEdit();
  const [fetchGraph] = useLazyGetHorizonGraphQuery();

  const { horizons } = useMapPlaces();

  useEffect(() => {
    if (horizons.length === 0) return;

    const isValid = hasValue(selectedHorizonId) && horizons.some((horizon) => horizon.id === selectedHorizonId);
    if (!isValid) {
      dispatch(mapActions.setSelectedHorizonId(horizons[0].id));
    }
  }, [horizons, selectedHorizonId, dispatch]);

  const handleSelectChange = async (value: string | null) => {
    const canProceed = await exitGraphEdit('Несохранённые изменения будут потеряны.');
    if (!canProceed) return;

    if (hasValue(value)) {
      const newHorizonId = Number(value);
      dispatch(mapActions.setSelectedHorizonId(newHorizonId));
      await fetchGraph(newHorizonId);
    }
  };

  if (horizons.length === 0) {
    return (
      <Select
        classNames={{
          input: styles.field,
        }}
        allowDeselect={false}
        withCheckIcon={false}
        variant="combobox-primary"
        inputSize="combobox-sm"
        labelPosition="vertical"
        data={EMPTY_ARRAY}
        value={null}
        placeholder="Не найдено"
        disabled
      />
    );
  }

  const options = horizons.map((horizon) => ({
    label: `${horizon.height} м`,
    value: String(horizon.id),
  }));

  return (
    <Select
      classNames={{
        input: styles.field,
      }}
      allowDeselect={false}
      withCheckIcon={false}
      variant="combobox-primary"
      inputSize="combobox-sm"
      labelPosition="vertical"
      data={options}
      value={hasValue(selectedHorizonId) ? String(selectedHorizonId) : null}
      onChange={handleSelectChange}
    />
  );
}
