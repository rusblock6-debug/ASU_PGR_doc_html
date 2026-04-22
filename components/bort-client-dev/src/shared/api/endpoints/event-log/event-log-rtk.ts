import { rtkApi } from '@/shared/api/rtk-api';

import type { CurrentShiftStatsResponse } from './types';

const eventLogApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getCurrentShiftStats: build.query<CurrentShiftStatsResponse, string>({
      query: (vehicleId) => {
        const params = new URLSearchParams({ vehicle_id: vehicleId });
        return `/event-log/current-shift-stats?${params.toString()}`;
      },
    }),
  }),
});

export const { useGetCurrentShiftStatsQuery } = eventLogApi;
