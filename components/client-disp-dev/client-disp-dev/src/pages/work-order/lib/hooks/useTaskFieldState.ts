import { hasValue } from '@/shared/lib/has-value';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { BlockReason, getBlockReasonMessage } from '../../model/block-reasons';
import { EDITABLE_STATUSES, REQUIRED_FIELDS } from '../../model/constants';
import { selectValidationError, selectValidationWarning } from '../../model/selectors';
import type { RouteTaskDraft, RouteTaskEditableField } from '../../model/types';
import { getWarningReasonMessage } from '../../model/warning-reasons';

/**
 * Представляет свойства для поля маршрутного задания.
 *
 * - `withAsterisk` отображать ли маркер обязательного поля.
 * - `error` есть ли ошибка валидации для данного поля.
 */
interface FieldProps {
  readonly withAsterisk: boolean;
  readonly error: boolean;
}

/**
 * Представляет свойства для поля маршрутного задания.
 *
 * - `withAsterisk` отображать ли маркер обязательного поля.
 * - `error` есть ли ошибка валидации для данного поля.
 * - `warning` есть ли предупреждение валидации для данного поля.
 */
interface FieldPropsWithWarning extends FieldProps {
  readonly warning: boolean;
}

/**
 * Представляет параметры хука {@link useTaskFieldState}.
 */
interface UseTaskFieldStateOptions {
  /** ID задачи. */
  readonly taskId: string;
  /** Данные маршрутного задания. */
  readonly task: RouteTaskDraft | null;
}

/**
 * Хук для управления состоянием полей маршрутного задания.
 *
 * Возвращает:
 * - `isBlocked` задание полностью заблокировано (нет груза или статус не позволяет редактировать).
 * - `isLinkedFieldsBlocked` связанные поля (объём, вес, рейсы) заблокированы.
 * - `errorMessage` текст сообщения об ошибке.
 * - `warningMessage` текст сообщения с предупреждением.
 * - `getFieldProps` функция для получения props поля (withAsterisk, error).
 * - `getFieldPropsWithWarning` функция для получения props поля (withAsterisk, error, warning).
 */
export function useTaskFieldState({ taskId, task }: UseTaskFieldStateOptions) {
  const blockState = useAppSelector((state) => selectValidationError(state, taskId));
  const blockReason = blockState?.reason ?? null;

  const warningState = useAppSelector((state) => selectValidationWarning(state, taskId));

  // Блокировка по статусу — задание уже в работе и не может быть отредактировано
  const isStatusLocked = hasValue(task) ? !EDITABLE_STATUSES.has(task.status) : false;

  // Связанные поля заблокированы для всех причин, кроме случая когда поля должны быть заполнены все
  const isLinkedFieldsBlocked = isStatusLocked || (blockState && blockReason !== BlockReason.REQUIRED_FIELDS);

  const hasFieldError = (field: RouteTaskEditableField) => blockState?.errorFields.includes(field) ?? false;

  const hasFieldWarning = (field: RouteTaskEditableField) => warningState?.warningFields.includes(field) ?? false;

  const errorMessage = getBlockReasonMessage(blockState);

  const warningMessage = getWarningReasonMessage(warningState?.reason);

  const getFieldProps = (field: RouteTaskEditableField): FieldProps => ({
    withAsterisk: isFieldRequired(field),
    error: hasFieldError(field),
  });

  const getFieldPropsWithWarning = (field: RouteTaskEditableField): FieldPropsWithWarning => ({
    ...getFieldProps(field),
    warning: hasFieldWarning(field),
  });

  return {
    isBlocked: isStatusLocked,
    isLinkedFieldsBlocked,
    errorMessage,
    warningMessage,
    getFieldProps,
    getFieldPropsWithWarning,
  };
}

/** Проверяет, является ли поле обязательным. */
function isFieldRequired(field: RouteTaskEditableField) {
  return REQUIRED_FIELDS.includes(field);
}
