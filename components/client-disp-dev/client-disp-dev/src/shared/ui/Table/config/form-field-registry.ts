import { z } from 'zod';

import { EMPTY_ARRAY } from '@/shared/lib/constants';
import {
  createCoordinatesSchema,
  DATE_VALIDATION,
  MULTI_CATEGORY_VALIDATION,
  NUMBER_VALIDATION,
  SELECT_VALIDATION,
  STRING_VALIDATION,
  TIME_VALIDATION,
  withRequired,
} from '@/shared/lib/validation';
import { EMPTY_COORDINATES, type LocationModel } from '@/shared/models/LocationModel';

import type { StrictColumnMeta } from '../model/column-meta';
import { type ColumnDataType, ColumnDataTypes, type FieldComponent } from '../types';
import { AutocompleteTextField } from '../ui/FormField/AutocompleteTextField';
import { ColorField } from '../ui/FormField/ColorField';
import { CoordinatesField } from '../ui/FormField/CoordinatesField';
import { DateField } from '../ui/FormField/DateField';
import { DateTimeField } from '../ui/FormField/DateTimeField';
import { EditableSelectField } from '../ui/FormField/EditableSelectField';
import { MultiSelectField } from '../ui/FormField/MultiSelectField';
import { NumberField } from '../ui/FormField/NumberField';
import { PasswordField } from '../ui/FormField/PasswordField';
import { SelectField } from '../ui/FormField/SelectField';
import { TextField } from '../ui/FormField/TextField';
import { TimeField } from '../ui/FormField/TimeField';

/** Конфигурация типа поля. */
interface FieldTypeConfig {
  /** Возвращает компонент для рендеринга поля формы. */
  readonly component: FieldComponent;
  /** Возвращает дефолтное значение для поля. Вызывается при инициализации формы. */
  readonly getDefaultValue: (value: unknown, meta?: StrictColumnMeta) => unknown;
  /** Возвращает схему валидации для поля. */
  readonly getValidationSchema: (required: boolean, meta?: StrictColumnMeta) => z.ZodType;
}

/**
 * Реестр типов полей формы.
 * Определяет для каждого типа — компонент, дефолтное значение и схему валидации.
 */
const formFieldRegistry: Record<ColumnDataType, FieldTypeConfig> = {
  [ColumnDataTypes.TEXT]: {
    component: TextField,
    getDefaultValue: (value) => value,
    getValidationSchema: withRequired(STRING_VALIDATION),
  },

  [ColumnDataTypes.AUTOCOMPLETE_TEXT]: {
    component: AutocompleteTextField,
    getDefaultValue: (value) => value,
    getValidationSchema: withRequired(STRING_VALIDATION),
  },

  [ColumnDataTypes.NUMBER]: {
    component: NumberField,
    getDefaultValue: (value) => value,
    getValidationSchema: withRequired(NUMBER_VALIDATION),
  },

  [ColumnDataTypes.DATE]: {
    component: DateField,
    getDefaultValue: (value) => value,
    getValidationSchema: withRequired(DATE_VALIDATION),
  },

  [ColumnDataTypes.DATETIME]: {
    component: DateTimeField,
    getDefaultValue: (value) => value,
    getValidationSchema: withRequired(DATE_VALIDATION),
  },

  [ColumnDataTypes.TIME]: {
    component: TimeField,
    getDefaultValue: (value) => value ?? '00:00',
    getValidationSchema: withRequired(TIME_VALIDATION),
  },

  [ColumnDataTypes.SELECT]: {
    component: SelectField,
    getDefaultValue: (value) => value,
    getValidationSchema: withRequired(SELECT_VALIDATION),
  },

  [ColumnDataTypes.MULTI_SELECT]: {
    component: MultiSelectField,
    getDefaultValue: (value) => (value as { id: number }[] | undefined)?.map((item) => String(item.id)) ?? EMPTY_ARRAY,
    getValidationSchema: withRequired(MULTI_CATEGORY_VALIDATION),
  },

  [ColumnDataTypes.EDITABLE_SELECT]: {
    component: EditableSelectField,
    getDefaultValue: (value) => value,
    getValidationSchema: withRequired(SELECT_VALIDATION),
  },

  [ColumnDataTypes.COORDINATES]: {
    component: CoordinatesField,
    getDefaultValue: (value) => {
      if (!value || typeof value !== 'object') {
        return EMPTY_COORDINATES;
      }

      const coords = value as LocationModel;
      if ('lat' in coords || 'lon' in coords) {
        return { lat: coords.lat ?? undefined, lon: coords.lon ?? undefined };
      }

      return EMPTY_COORDINATES;
    },
    getValidationSchema: createCoordinatesSchema,
  },

  [ColumnDataTypes.COLOR]: {
    component: ColorField,
    getDefaultValue: (value) => value,
    getValidationSchema: withRequired(STRING_VALIDATION),
  },
  [ColumnDataTypes.PASSWORD]: {
    component: PasswordField,
    getDefaultValue: (value) => value,
    getValidationSchema: withRequired(STRING_VALIDATION),
  },
};

/** Получить компонент поля по типу данных колонки */
export function getFieldComponent(dataType: ColumnDataType) {
  return formFieldRegistry[dataType].component;
}

/** Получить дефолтное значение для поля по типу данных колонки */
export function getFieldDefaultValue(dataType: ColumnDataType, value: unknown, meta?: StrictColumnMeta) {
  return formFieldRegistry[dataType].getDefaultValue(value, meta);
}

/** Получить схему валидации для поля по типу данных колонки */
export function getFieldValidationSchema(dataType: ColumnDataType, required: boolean, meta?: StrictColumnMeta) {
  // Кастомная валидация из meta имеет приоритет
  if (meta?.validation) {
    return withRequired(meta.validation)(required);
  }

  return formFieldRegistry[dataType].getValidationSchema(required, meta);
}
