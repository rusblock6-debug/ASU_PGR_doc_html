import { useMemo } from 'react';

import { createTimezoneFormatter } from '../timezone';

export function useTimezone() {
  const timezone = 'Europe/Moscow';

  return useMemo(() => createTimezoneFormatter(timezone), [timezone]);
}
