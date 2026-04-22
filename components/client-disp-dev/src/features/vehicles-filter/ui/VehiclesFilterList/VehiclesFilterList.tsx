import { type ChangeEvent, useCallback, useMemo, useState } from 'react';

import { getVehicleTypeDisplayName } from '@/entities/vehicle';

import type { Vehicle, VehicleType } from '@/shared/api/endpoints/vehicles';
import ArrowDownIcon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import { Checkbox } from '@/shared/ui/Checkbox';
import { Menu } from '@/shared/ui/Menu';
import { ScrollArea } from '@/shared/ui/ScrollArea';
import { TextInput } from '@/shared/ui/TextInput';

import styles from './VehiclesFilterList.module.css';

/** Представляет свойства компонента списка транспортных средств для фильтрации. */
interface VehiclesFilterListProps {
  /** Возвращает тип транспортных средств. */
  readonly vehicleType: VehicleType;
  /** Возвращает список транспортных средств. */
  readonly vehicles: readonly Vehicle[];
  /** Возвращает список идентификаторов выбранных транспортных средств для фильтрации. */
  readonly selectedVehicleIds: Set<number>;
  /** Возвращает делегат, вызываемый при добавлении элементов фильтрации. */
  readonly onAddVehiclesFromFilter: (vehicleIds: readonly number[]) => void;
  /** Возвращает делегат, вызываемый при удалении элементов фильтрации. */
  readonly onRemoveVehiclesFromFilter: (vehicleIds: readonly number[]) => void;
}

/**
 * Представляет компонент списка транспортных средств для фильтрации.
 */
export function VehiclesFilterList(props: VehiclesFilterListProps) {
  const { vehicleType, vehicles, selectedVehicleIds, onAddVehiclesFromFilter, onRemoveVehiclesFromFilter } = props;

  const [inputValue, setInputValue] = useState('');

  const onInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    setInputValue(event.target.value);
  };

  const onInputClear = () => {
    setInputValue('');
  };

  const filteredVehicles = useMemo(
    () => vehicles.filter((vehicle) => vehicle.name.trim().toLowerCase().includes(inputValue.trim().toLowerCase())),
    [inputValue, vehicles],
  );

  const filteredVehicleIds = useMemo<readonly number[]>(
    () => filteredVehicles.map((item) => item.id),
    [filteredVehicles],
  );

  const selectAllHandler = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      if (event.target.checked) {
        onAddVehiclesFromFilter(filteredVehicleIds);
      } else {
        onRemoveVehiclesFromFilter(filteredVehicleIds);
      }
    },
    [filteredVehicleIds, onAddVehiclesFromFilter, onRemoveVehiclesFromFilter],
  );

  return (
    <Menu.Sub
      offset={12}
      closeDelay={300}
      openDelay={300}
    >
      <Menu.Sub.Target>
        <Menu.Sub.Item rightSection={<ArrowDownIcon className={styles.sub_menu_arrow} />}>
          {getVehicleTypeDisplayName(vehicleType)}
        </Menu.Sub.Item>
      </Menu.Sub.Target>

      <Menu.Sub.Dropdown>
        <div className={styles.dropdown_container}>
          <TextInput
            placeholder="Поиск"
            variant="outline"
            clearable
            className={styles.input}
            value={inputValue}
            onChange={onInputChange}
            onClear={onInputClear}
          />
          {filteredVehicles.length > 0 ? (
            <>
              <label className={styles.list_item}>
                <Checkbox
                  size="xs"
                  onChange={selectAllHandler}
                />
                <p>Выбрать все</p>
              </label>
              <ScrollArea.Autosize mah="70vh">
                <div className={styles.vehicle_list_container}>
                  {filteredVehicles.map((item) => (
                    <label
                      key={item.id}
                      className={styles.list_item}
                    >
                      <Checkbox
                        size="xs"
                        checked={selectedVehicleIds.has(item.id)}
                        onChange={(event) =>
                          event.target.checked
                            ? onAddVehiclesFromFilter([item.id])
                            : onRemoveVehiclesFromFilter([item.id])
                        }
                      />
                      <p>{item.name}</p>
                    </label>
                  ))}
                </div>
              </ScrollArea.Autosize>
            </>
          ) : (
            <div className={styles.no_data}>Нет данных</div>
          )}
        </div>
      </Menu.Sub.Dropdown>
    </Menu.Sub>
  );
}
