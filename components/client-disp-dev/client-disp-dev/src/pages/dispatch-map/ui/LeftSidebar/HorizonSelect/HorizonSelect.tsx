import { useEffect } from 'react';

import { useGetAllHorizonsQuery } from '@/shared/api/endpoints/horizons';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { Select } from '@/shared/ui/Select';

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

  const { data: horizonsData } = useGetAllHorizonsQuery();
  const horizons = horizonsData?.items ?? EMPTY_ARRAY;

  useEffect(() => {
    if (horizons.length === 0) return;

    const isValid = hasValue(selectedHorizonId) && horizons.some((horizon) => horizon.id === selectedHorizonId);
    if (!isValid) {
      dispatch(mapActions.setSelectedHorizonId(horizons[0].id));
    }
  }, [horizons, selectedHorizonId, dispatch]);

  const onSelectChange = (value: string | null) => {
    if (hasValue(value)) {
      dispatch(mapActions.setSelectedHorizonId(Number(value)));
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

  const options = [...horizons]
    .sort((a, b) => b.height - a.height)
    .map((horizon) => ({
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
      onChange={onSelectChange}
    />
  );
}
