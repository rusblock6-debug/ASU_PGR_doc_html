import { useCombobox } from '@mantine/core';
import { useEffect } from 'react';

/**
 * Хук для автоматического выделения опции «Создать» при вводе текста.
 * Если showCreateOption === true, выделяет первую опцию (которая является опцией создания).
 * Иначе сбрасывает выделение при открытии dropdown.
 */
export function useAutoSelectCreateOption(showCreateOption: boolean, combobox: ReturnType<typeof useCombobox>) {
  useEffect(() => {
    if (showCreateOption && combobox.dropdownOpened) {
      combobox.selectFirstOption();
    } else if (combobox.dropdownOpened) {
      combobox.resetSelectedOption();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showCreateOption, combobox.dropdownOpened]);
}
