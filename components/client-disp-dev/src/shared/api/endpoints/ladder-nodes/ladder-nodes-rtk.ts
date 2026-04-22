import { rtkApi } from '@/shared/api';
import { toHTTPError } from '@/shared/api/types';

import type { LadderConnectRequest, LadderConnectResponse } from './types';

export const ladderNodeRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    connectLadderNodes: build.mutation<LadderConnectResponse, LadderConnectRequest>({
      query: (body) => ({
        url: '/graph/ladder-nodes/connect',
        method: 'POST',
        body,
      }),

      transformErrorResponse: toHTTPError,

      invalidatesTags: ['Ladders', 'Horizons'],
    }),

    deleteLadderNode: build.mutation<void, number>({
      query: (nodeId) => ({
        url: `/graph/ladder-nodes/${nodeId}`,
        method: 'DELETE',
      }),

      transformErrorResponse: toHTTPError,

      invalidatesTags: ['Ladders', 'Horizons'],
    }),
  }),
});

export const { useConnectLadderNodesMutation, useDeleteLadderNodeMutation } = ladderNodeRtkApi;
