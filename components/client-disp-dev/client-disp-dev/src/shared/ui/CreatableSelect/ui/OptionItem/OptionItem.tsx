import { Combobox } from '@mantine/core';
import React, { useEffect, useRef, useState } from 'react';

import ThreeDotsIcon from '@/shared/assets/icons/ic-three-dots.svg?react';
import TrashIcon from '@/shared/assets/icons/ic-trash.svg?react';
import { Z_INDEX } from '@/shared/lib/constants';
import { Popover } from '@/shared/ui/Popover';
import { TextInput } from '@/shared/ui/TextInput';
import type { SelectOption } from '@/shared/ui/types';

import type { EditingState } from '../../lib/types';

import styles from './OptionItem.module.css';

/** Представляет свойства компонента опции. */
export interface OptionItemProps<T extends SelectOption> {
  readonly option: T;
  readonly editing: EditingState;
  readonly showMenu: boolean;
  readonly showCreateOption: boolean;
  readonly filteredOptions: readonly T[];
  readonly onOpenMenu: (option: T) => void;
  readonly onEditLabelChange: (label: string) => void;
  readonly onFinishEditing: () => void;
  readonly onDelete: (optionValue: string) => void;
  readonly onSelectOption: (index: number) => void;
  readonly hasRename: boolean;
  readonly hasDelete: boolean;
}

/**
 * Представляет компонент опции.
 */
export function OptionItem<T extends SelectOption>({
  option,
  editing,
  showMenu,
  showCreateOption,
  filteredOptions,
  onOpenMenu,
  onEditLabelChange,
  onFinishEditing,
  onDelete,
  onSelectOption,
  hasRename,
  hasDelete,
}: OptionItemProps<T>) {
  const optionRef = useRef<HTMLDivElement>(null);
  const [optionWidth, setOptionWidth] = useState<number | null>(null);

  const isEditing = editing?.value === option.value;

  // Измеряем ширину опции при открытии меню
  useEffect(() => {
    if (isEditing && optionRef.current) {
      setOptionWidth(optionRef.current.offsetWidth);
    }
  }, [isEditing]);

  const handlePopoverButtonClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    onOpenMenu(option);

    // Делаем пункт активным при открытии поповера
    const optionIndex = filteredOptions.findIndex((o) => o.value === option.value);
    if (optionIndex !== -1) {
      // Учитываем опцию «Создать», которая идёт первой
      const actualIndex = showCreateOption ? optionIndex + 1 : optionIndex;
      onSelectOption(actualIndex);
    }
  };

  const handleRenameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === 'Escape') {
      e.preventDefault();
      onFinishEditing();
    }
  };

  return (
    <Combobox.Option value={option.value}>
      <div
        ref={optionRef}
        className={styles.option_content}
      >
        <span
          className={styles.option_label}
          title={option.label}
        >
          {option.label}
        </span>

        {showMenu && (
          <Popover
            zIndex={Z_INDEX.FIXED}
            opened={isEditing}
            onClose={onFinishEditing}
            position="bottom-end"
            offset={2}
            withinPortal
            classNames={{ dropdown: styles.option_menu_dropdown }}
            styles={{
              dropdown: {
                width: optionWidth ?? 'auto',
              },
            }}
          >
            <Popover.Target>
              <button
                type="button"
                className={styles.option_menu_button}
                data-menu-button="true"
                onClick={handlePopoverButtonClick}
              >
                <ThreeDotsIcon />
              </button>
            </Popover.Target>

            <Popover.Dropdown
              onMouseDown={(e) => e.stopPropagation()}
              onClick={(e) => e.stopPropagation()}
            >
              <div className={styles.option_menu}>
                {hasRename && (
                  <TextInput
                    inputSize="sm"
                    variant="outline"
                    labelPosition="vertical"
                    autoFocus
                    value={editing?.label ?? ''}
                    placeholder="Название"
                    clearable={!!editing?.label}
                    onKeyDown={handleRenameKeyDown}
                    onChange={(e) => onEditLabelChange(e.currentTarget.value)}
                    onFocus={(e) => e.currentTarget.select()}
                    onClear={() => onEditLabelChange('')}
                  />
                )}

                {hasDelete && (
                  <button
                    type="button"
                    className={styles.delete_button}
                    onClick={() => onDelete(option.value)}
                  >
                    <TrashIcon
                      width={12}
                      height={12}
                    />
                    <span>Удалить</span>
                  </button>
                )}
              </div>
            </Popover.Dropdown>
          </Popover>
        )}
      </div>
    </Combobox.Option>
  );
}
