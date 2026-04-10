import { useCallback } from 'react';

import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { selectIsTreeNodeExpanded } from '../../model/selectors';
import { mapActions } from '../../model/slice';
import type { TreeNodeValue } from '../../model/types';

/**
 * Состояние раздела (раскрыт/свёрнут) и функция переключения.
 */
export function useTreeNodeExpanded(key: TreeNodeValue) {
  const isExpanded = useAppSelector((state) => selectIsTreeNodeExpanded(state, key));
  const dispatch = useAppDispatch();
  const toggle = useCallback(() => dispatch(mapActions.toggleTreeNode(key)), [dispatch, key]);

  return [isExpanded, toggle] as const;
}
