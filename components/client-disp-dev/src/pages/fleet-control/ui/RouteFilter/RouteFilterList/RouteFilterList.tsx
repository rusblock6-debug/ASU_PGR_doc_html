import { type ChangeEvent, useCallback, useState } from 'react';

import ArrowDownIcon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import { Checkbox } from '@/shared/ui/Checkbox';
import { Menu } from '@/shared/ui/Menu';
import { ScrollArea } from '@/shared/ui/ScrollArea';
import { TextInput } from '@/shared/ui/TextInput';

import styles from './RouteFilterList.module.css';

/**
 * Представляет модель элемента фильтра маршрутов.
 */
export interface RouteFilterItem {
  /** Возвращает идентификатор маршрута. */
  readonly route_id: string;
  /** Возвращает наименование пункта погрузки. */
  readonly place_a_name: string;
  /** Возвращает наименование пункта разгрузки. */
  readonly place_b_name: string;
}

/**
 * Представляет свойства компонента списка транспортных средств для фильтрации.
 */
interface RouteFilterListProps {
  /** Возвращает тип транспортных средств. */
  readonly sectionName: string;
  /** Возвращает список транспортных средств. */
  readonly routes: readonly RouteFilterItem[];
  /** Возвращает список идентификаторов выбранных транспортных средств для фильтрации. */
  readonly selectedRouteIds: Set<string>;
  /** Возвращает делегат, вызываемый при добавлении элементов фильтрации. */
  readonly onAddRoutesFromFilter: (routeIds: readonly string[]) => void;
  /** Возвращает делегат, вызываемый при удалении элементов фильтрации. */
  readonly onRemoveRoutesFromFilter: (routeIds: readonly string[]) => void;
}

/**
 * Представляет компонент списка маршрутов.
 */
export function RouteFilterList(props: RouteFilterListProps) {
  const { sectionName, routes, selectedRouteIds, onAddRoutesFromFilter, onRemoveRoutesFromFilter } = props;

  const [inputValue, setInputValue] = useState('');

  const onInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    setInputValue(event.target.value);
  };

  const onInputClear = () => {
    setInputValue('');
  };

  const filteredRoutes = routes.filter(
    (route) =>
      route.place_a_name.trim().toLowerCase().includes(inputValue.trim().toLowerCase()) ||
      route.place_b_name.trim().toLowerCase().includes(inputValue.trim().toLowerCase()),
  );

  const filteredRouteIds = filteredRoutes.map((item) => item.route_id);

  const selectAllHandler = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      if (event.target.checked) {
        onAddRoutesFromFilter(filteredRouteIds);
      } else {
        onRemoveRoutesFromFilter(filteredRouteIds);
      }
    },
    [filteredRouteIds, onAddRoutesFromFilter, onRemoveRoutesFromFilter],
  );

  return (
    <Menu.Sub
      offset={12}
      closeDelay={300}
      openDelay={300}
    >
      <Menu.Sub.Target>
        <Menu.Sub.Item rightSection={<ArrowDownIcon className={styles.sub_menu_arrow} />}>{sectionName}</Menu.Sub.Item>
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
          {filteredRoutes.length > 0 ? (
            <>
              <div className={styles.list_item}>
                <Checkbox
                  size="xs"
                  onChange={selectAllHandler}
                />
                <p>Выбрать все</p>
              </div>
              <ScrollArea.Autosize mah="70vh">
                <div className={styles.route_list_container}>
                  {filteredRoutes.map((item) => (
                    <div
                      key={item.route_id}
                      className={styles.list_item}
                    >
                      <Checkbox
                        size="xs"
                        checked={selectedRouteIds.has(item.route_id)}
                        onChange={(event) =>
                          event.target.checked
                            ? onAddRoutesFromFilter([item.route_id])
                            : onRemoveRoutesFromFilter([item.route_id])
                        }
                      />
                      <p>
                        {item.place_a_name} — {item.place_b_name}
                      </p>
                    </div>
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
