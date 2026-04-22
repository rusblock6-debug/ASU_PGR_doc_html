import { useState } from 'react';

import { hasValue } from '@/shared/lib/has-value';
import type { SelectOption } from '@/shared/ui/types';

import type { EditingState } from '../types';

/**
 * Хук для управления состоянием редактирования опции.
 */
export function useEditingState() {
  const [editing, setEditing] = useState<EditingState>(null);

  const startEditing = (option: SelectOption) => {
    setEditing(option);
  };

  const stopEditing = () => {
    setEditing(null);
  };

  const updateLabel = (label: string) => {
    setEditing((prev) => (prev ? { ...prev, label } : null));
  };

  return {
    editing,
    isEditing: hasValue(editing),
    startEditing,
    stopEditing,
    updateLabel,
  };
}
