import { rtkApi } from '@/shared/api';
import { DEFAULT_ENTERPRISE_ID } from '@/shared/config/constants';

import type { WorkRegimeQueryArg, WorkRegimeResponse } from './types';

export const workRegimesRtkApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    getAllWorkRegimes: builder.query<WorkRegimeResponse, WorkRegimeQueryArg | void>({
      query: (queryArg) => {
        const params = new URLSearchParams();

        const enterpriseId = queryArg?.enterprise_id ?? DEFAULT_ENTERPRISE_ID;
        params.append('enterprise_id', String(enterpriseId));

        return `/work-regimes?${params}`;
      },
    }),
  }),
});

export const { useGetAllWorkRegimesQuery } = workRegimesRtkApi;
