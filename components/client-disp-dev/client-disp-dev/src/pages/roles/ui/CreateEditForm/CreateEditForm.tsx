import { zodResolver } from '@hookform/resolvers/zod';
import React from 'react';
import { Controller, useForm } from 'react-hook-form';
import { z } from 'zod';

import {
  type CreateRoleRequest,
  type Role,
  type UpdateRoleRequest,
  useCreateRoleMutation,
  useUpdateRoleMutation,
} from '@/shared/api/endpoints/roles';
import type { RolePermission } from '@/shared/api/endpoints/roles/types';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { cn } from '@/shared/lib/classnames-utils';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { STRING_VALIDATION } from '@/shared/lib/validation';
import { navLinks } from '@/shared/routes/navigation';
import { AppButton } from '@/shared/ui/AppButton';
import { Radio } from '@/shared/ui/Radio';
import { TextInput } from '@/shared/ui/TextInput';
import { toast } from '@/shared/ui/Toast';

import styles from './CreateEditForm.module.css';

const PERMISSION_LEVEL = {
  NOT_AVAILABLE: 'notAvailable',
  CAN_VIEW: 'canView',
  CAN_EDIT: 'canEdit',
} as const;

type Permissions = Record<string, RolePermission>;

/**
 * Представляет состояние формы.
 */
interface FormState {
  /** Возвращает наименование роли. */
  readonly name: string;
  /** Возвращает список доступов. */
  readonly permissions: Permissions;
}

const rolePermissionSchema = z.object({
  name: z.string(),
  can_view: z.boolean(),
  can_edit: z.boolean(),
});

/**
 * Представляет свойства компонента формы создания/редактирования роли.
 */
interface CreateEditFormProps {
  /** Возвращает признак, что форма находится в режиме создания. */
  readonly addMode: boolean;
  /** Возвращает делегат, вызываемый при  закрытии формы. */
  readonly onClose: () => void;
  /** Возвращает редактируемую роль. */
  readonly role: Role | null;
}

/**
 * Представляет компонент формы создания/редактирования роли.
 */
export function CreateEditForm(props: CreateEditFormProps) {
  const { addMode, onClose, role } = props;

  const [createRole] = useCreateRoleMutation();
  const [updateRole] = useUpdateRoleMutation();

  const {
    control,
    handleSubmit,
    formState: { isSubmitting, isDirty, isValid },
  } = useForm<FormState>({
    defaultValues: {
      name: addMode ? '' : role?.name || '',
      permissions: Object.fromEntries(
        role?.permissions.map((permission) => [permission.name, permission]) ?? EMPTY_ARRAY,
      ),
    },
    mode: 'onChange',
    resolver: zodResolver(
      z.object({ name: STRING_VALIDATION, permissions: z.record(z.string(), rolePermissionSchema) }),
    ),
  });

  const handleAdd = async (newRole: CreateRoleRequest) => {
    const { name, ...data } = newRole;
    assertHasValue(name);

    const request = createRole({ name, ...data }).unwrap();

    await toast.promise(request, {
      loading: {
        message: `Добавление новой роли «${name}»`,
      },
      success: {
        message: `Добавлена новая роль «${name}»`,
      },
      error: {
        message: 'Ошибка добавления',
      },
    });
  };

  const handleEdit = async (editingRole: UpdateRoleRequest) => {
    if (role) {
      const { name, ...data } = editingRole;

      const request = updateRole({
        id: role.id,
        body: { name, ...data },
      }).unwrap();

      await toast.promise(request, {
        loading: {
          message: `Редактирование роли «${name}»`,
        },
        success: {
          message: `Изменена роль «${name}»`,
        },
        error: {
          message: 'Ошибка редактирования',
        },
      });
    }
  };

  const onSubmit = async (data: FormState) => {
    const requestData = {
      name: data.name,
      permissions: Object.values(data.permissions),
    };

    if (addMode) {
      await handleAdd(requestData);
    } else if (role) {
      await handleEdit(requestData);
    }
    onClose();
  };

  const handleEnterSubmit = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      event.preventDefault();
    }
  };

  const disabledSubmitButton = isSubmitting || !isDirty || !isValid;

  const activeNavLinks = navLinks.filter((link) => link.items?.some((item) => hasValue(item.key)));

  const createPermissionChangeHandler =
    (itemKey: string, value: Permissions, onChange: (v: Permissions) => void) => (radioValue: string) => {
      assertHasValue(itemKey);

      const newValue = { ...value };

      if (radioValue === PERMISSION_LEVEL.NOT_AVAILABLE) {
        delete newValue[itemKey];
      } else {
        newValue[itemKey] = getNewPermission(itemKey, radioValue);
      }

      onChange(newValue);
    };

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      onKeyDown={handleEnterSubmit}
      className={styles.root}
    >
      <div className={styles.inputs_container}>
        <Controller
          name="name"
          control={control}
          render={({ field: { value, onChange, onBlur }, fieldState }) => (
            <TextInput
              onBlur={onBlur}
              value={value}
              onChange={onChange}
              label="Наименование роли"
              error={fieldState.error?.message}
              withAsterisk
            />
          )}
        />
        <Controller
          name="permissions"
          control={control}
          render={({ field: { value, onChange } }) => (
            <div className={styles.available_forms}>
              <p className={styles.available_forms_title}>Доступные формы</p>
              <div className={styles.available_forms_container}>
                {activeNavLinks.map((group) => (
                  <div
                    key={group.title}
                    className={styles.available_form_group_container}
                  >
                    <div className={styles.available_forms_group_title_container}>
                      <p className={cn(styles.available_forms_group_title, styles.left_column)}>{group.title}</p>
                      <p className={styles.available_form_column_title}>Нет доступа</p>
                      <p className={styles.available_form_column_title}>Просмотр</p>
                      <p className={styles.available_form_column_title}>Редактирование</p>
                    </div>

                    {group.items
                      ?.filter((link) => hasValue(link.key))
                      .map((item) => {
                        assertHasValue(item.key);
                        const radioValue = getRadioValue(value[item.key]);

                        return (
                          <div
                            key={item.key}
                            className={styles.available_form_string}
                          >
                            <p className={cn(styles.available_form_title, styles.left_column)}>{item.title}</p>
                            <Radio.Group
                              value={radioValue}
                              onChange={createPermissionChangeHandler(item.key, value, onChange)}
                              className={styles.radio_group_container}
                            >
                              <div className={styles.radio_button_container}>
                                <Radio
                                  size="xs"
                                  value={PERMISSION_LEVEL.NOT_AVAILABLE}
                                />
                              </div>
                              <div className={styles.radio_button_container}>
                                <Radio
                                  size="xs"
                                  value={PERMISSION_LEVEL.CAN_VIEW}
                                />
                              </div>
                              <div className={styles.radio_button_container}>
                                <Radio
                                  size="xs"
                                  value={PERMISSION_LEVEL.CAN_EDIT}
                                />
                              </div>
                            </Radio.Group>
                          </div>
                        );
                      })}
                  </div>
                ))}
              </div>
            </div>
          )}
        />
      </div>
      <AppButton
        className={styles.button}
        type="submit"
        variant="primary"
        size="m"
        disabled={disabledSubmitButton}
        loading={isSubmitting}
      >
        Сохранить
      </AppButton>
    </form>
  );
}

/**
 * Возвращает значение радиокнопки.
 *
 * @param value данные доступа роли.
 */
function getRadioValue(value?: RolePermission) {
  if (value?.can_edit) {
    return PERMISSION_LEVEL.CAN_EDIT;
  }
  if (value?.can_view) {
    return PERMISSION_LEVEL.CAN_VIEW;
  }
  return PERMISSION_LEVEL.NOT_AVAILABLE;
}

/**
 * Возвращает новый доступ роли.
 *
 * @param name название формы для роли.
 * @param radioValue значение радиокнопки.
 */
function getNewPermission(name: string, radioValue: string) {
  return {
    name,
    can_edit: radioValue === PERMISSION_LEVEL.CAN_EDIT,
    can_view: radioValue === PERMISSION_LEVEL.CAN_VIEW || radioValue === PERMISSION_LEVEL.CAN_EDIT,
  } satisfies RolePermission;
}
