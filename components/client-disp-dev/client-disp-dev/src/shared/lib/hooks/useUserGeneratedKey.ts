import { useMemo } from 'react';

import { hasValue } from '@/shared/lib/has-value';

/**
 * Используется для генерации уникального ключа путем добавления идентификатора пользователя к предоставленному базовому ключу.
 *
 * @param baseKey Базовый ключ, к которому будет добавлен идентификатор пользователя.
 */
export function useUserGeneratedKey(baseKey: string): string | null {
  // null указан как временное решение. Заменить на корректное значение, когда появится возможность получать идентификатор пользователя из данных сессии.
  const userId = null;
  return useMemo(() => {
    if (!hasValue(userId)) {
      return baseKey;
    }
    return `${baseKey}_${userId}`;
  }, [baseKey, userId]);
}
