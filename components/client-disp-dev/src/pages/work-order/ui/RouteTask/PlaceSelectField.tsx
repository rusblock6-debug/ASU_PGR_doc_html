import { hasValue } from '@/shared/lib/has-value';
import { Select, type SelectProps } from '@/shared/ui/Select';
import type { SelectOption } from '@/shared/ui/types';

import type { FieldPropsWithWarning } from '../../lib/hooks/useTaskFieldState';

import { ReadonlyField } from './ReadonlyField';
import { findOptionLabel } from './RouteTask';

/**
 * Представляет свойства компонента {@link PlaceSelectField}.
 */
interface PlaceSelectFieldProps extends FieldPropsWithWarning {
  /** Подпись поля. */
  readonly label: string;
  /** Поле заблокировано — рендерится `ReadonlyField` вместо `Select`. */
  readonly isBlocked: boolean;
  /** Выбранное значение — идентификатор места. */
  readonly value: number | null;
  /** Опции выпадающего списка. */
  readonly options: readonly SelectOption[];
  /** Общие пропсы для `Select`, подготовленные родителем. */
  readonly selectProps: SelectPropsForPlaceField;
  /** Название груза для подписи под полем. Если `null` — подпись не рендерится. */
  readonly cargoName: string | null;
  /** Обработчик смены значения. */
  readonly onChange: (value: string | null) => void;
  /** Классы, прокидываемые из родителя, чтобы компонент не зависел от его css-модуля. */
  readonly classNames: {
    /** Класс для внешней обёртки */
    readonly wrapper: string;
    /** Класс для поля только для просмотра. */
    readonly readonlyField: string;
    /** Класс для подписи с видом груза. */
    readonly cargoLabel: string;
  };
}

/**
 * Представляет свойства компонента {@link PlaceSelectField}, прокидываемые в {@link Select}.
 */
type SelectPropsForPlaceField = Partial<
  Pick<
    SelectProps<string>,
    | 'variant'
    | 'inputSize'
    | 'labelPosition'
    | 'placeholder'
    | 'allowDeselect'
    | 'withCheckIcon'
    | 'disabled'
    | 'classNames'
  >
>;

/**
 * Представляет компонент выбора места (погрузки/разгрузки) с подписью вида груза.
 *
 * В зависимости от `isBlocked` рендерит `ReadonlyField` или `Select`. Если задан `cargoName`,
 * показывает подпись «Вид груза — …» под полем.
 */
export function PlaceSelectField({
  label,
  isBlocked,
  value,
  options,
  withAsterisk,
  error,
  warning,
  selectProps,
  cargoName,
  onChange,
  classNames,
}: PlaceSelectFieldProps) {
  const stringValue = toStringOrNull(value);

  return (
    <div className={classNames.wrapper}>
      {isBlocked ? (
        <ReadonlyField
          withAsterisk={withAsterisk}
          className={classNames.readonlyField}
          label={label}
          value={findOptionLabel(options, stringValue)}
        />
      ) : (
        <Select
          {...selectProps}
          withAsterisk={withAsterisk}
          error={error}
          warning={warning}
          label={label}
          data={options}
          value={stringValue}
          onChange={onChange}
          searchable
        />
      )}
      {cargoName && (
        <span
          title={cargoName}
          className={classNames.cargoLabel}
        >
          Вид&nbsp;груза&nbsp;— {cargoName}
        </span>
      )}
    </div>
  );
}

/** Привести числовое значение к строке или вернуть null. */
function toStringOrNull(value: number | null) {
  return hasValue(value) ? String(value) : null;
}
