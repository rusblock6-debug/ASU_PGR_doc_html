import { useState } from 'react';

import { useGetShiftLoadTypeVolumesQuery } from '@/shared/api/endpoints/fleet-control';
import Icon from '@/shared/assets/icons/ic-calendar-checkmark.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { formatNumber } from '@/shared/lib/format-number';
import { CreatableMultiSelect } from '@/shared/ui/CreatableSelect';
import { Tooltip } from '@/shared/ui/Tooltip';
import type { SelectOption } from '@/shared/ui/types';

import { useFleetControlPageDataSource } from '../../../lib/hooks/useFleetControlPageDataSource';
import { POLLING_INTERVAL } from '../../../model/constants';
import { useFleetControlPageContext } from '../../../model/FleetControlPageContext';

import styles from './ResultsByCargoType.module.css';

const TITLE_TEXT = 'Итоги по видам груза за текущую смену';

/**
 * Представляет компонент отображающий итоги по видам груза за текущую смену.
 */
export function ResultsByCargoType() {
  const { isOpenSidebar, handleChangeOpenSidebar } = useFleetControlPageContext();

  const { places, sections } = useFleetControlPageDataSource();

  const [selectedPlacesIds, setSelectedPlacesIds] = useState<readonly number[]>([]);

  const [selectedSectionIds, setSelectedSectionIds] = useState<readonly number[]>([]);

  const sectionsSelectOptions = sections.map((item) => ({ value: String(item.id), label: item.name }));

  const placesSelectOptions = places
    .filter(
      (item) =>
        item.type === 'unload' &&
        (selectedSectionIds.length === 0 || selectedSectionIds.some((id) => item.section_ids.includes(id))),
    )
    .map((item) => ({ value: String(item.id), label: item.name }));

  const handleSelectedSectionId = (options: readonly SelectOption[]) => {
    const newSelectedSectionIds = options.map((item) => Number(item.value));
    setSelectedSectionIds(newSelectedSectionIds);

    setSelectedPlacesIds((prevSelectedPlacesIds) =>
      prevSelectedPlacesIds.filter((placeId) => {
        // eslint-disable-next-line sonarjs/no-nested-functions
        const place = places.find((p) => p.id === placeId);
        return place
          ? place.type === 'unload' &&
              // eslint-disable-next-line sonarjs/no-nested-functions
              (newSelectedSectionIds.length === 0 || newSelectedSectionIds.some((id) => place.section_ids.includes(id)))
          : false;
      }),
    );
  };

  const { data } = useGetShiftLoadTypeVolumesQuery(
    {
      section_id: selectedSectionIds,
      place_id: selectedPlacesIds,
    },
    {
      refetchOnMountOrArgChange: true,
      pollingInterval: POLLING_INTERVAL.RARELY,
    },
  );

  const dataSource = data?.items ?? EMPTY_ARRAY;

  return (
    <div className={cn(styles.root, { [styles.close]: !isOpenSidebar })}>
      <div className={styles.header}>
        <Tooltip
          label={TITLE_TEXT}
          disabled={isOpenSidebar}
        >
          <Icon
            className={cn(styles.icon, { [styles.close]: !isOpenSidebar })}
            onClick={() => handleChangeOpenSidebar(true)}
          />
        </Tooltip>
        {isOpenSidebar && <p className={styles.title}>{TITLE_TEXT}</p>}
      </div>
      {isOpenSidebar && (
        <div className={styles.table}>
          <div className={styles.table_row}>
            <div>
              <p className={styles.cargo_type}>Вид груза</p>
            </div>
            <div>
              <CreatableMultiSelect
                value={selectedSectionIds.map((item) => String(item))}
                options={sectionsSelectOptions}
                onChange={handleSelectedSectionId}
                placeholder="Все участки"
              />
            </div>
            <div>
              <CreatableMultiSelect
                value={selectedPlacesIds.map((item) => String(item))}
                options={placesSelectOptions}
                onChange={(options) => setSelectedPlacesIds(options.map((item) => Number(item.value)))}
                placeholder="Пункт разгрузки"
              />
            </div>
          </div>

          {dataSource.length > 0 ? (
            dataSource.map((row, index) => (
              <div
                key={row.load_type_id}
                className={cn(styles.table_row, { [styles.last]: index === dataSource.length - 1 })}
              >
                <div className={styles.table_cell}>{row.load_type_name}</div>
                <div className={styles.table_cell}>{formatNumber(Math.round(row.volume_sections_m3))} м³</div>
                <div className={styles.table_cell}>{formatNumber(Math.round(row.volume_places_m3))} м³</div>
              </div>
            ))
          ) : (
            <div className={styles.no_data}>Нет данных</div>
          )}
        </div>
      )}
    </div>
  );
}
