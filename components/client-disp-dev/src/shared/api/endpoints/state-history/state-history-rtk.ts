import { rtkApi } from '@/shared/api';

import type {
  CreateUpdateStateHistoryRequest,
  CreateUpdateStateHistoryResponse,
  DeleteStateHistoryRequest,
  DeleteStateHistoryResponse,
  StateHistoryLastStateQueryArgs,
  StateHistoryLastStateResponse,
  StateHistoryQueryArg,
  StateHistoryResponse,
} from './types';

export const stateHistoryRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getAllStateHistory: build.query<StateHistoryResponse, StateHistoryQueryArg>({
      query(queryArg) {
        const params = new URLSearchParams();

        params.append('from_date', queryArg.fromDate);
        params.append('to_date', queryArg.toDate);
        params.append('from_shift_num', String(queryArg.fromShiftNum));
        params.append('to_shift_num', String(queryArg.toShiftNum));

        if (queryArg.vehicleIds) {
          queryArg.vehicleIds.forEach((id) => {
            params.append('vehicle_ids', String(id));
          });
        }

        if (queryArg.isFullShift) {
          params.append('is_full_shift', String(queryArg.isFullShift));
        }

        return `/trip/event-log/state-history?${params}`;
      },
    }),

    getStateHistoryLastState: build.query<StateHistoryLastStateResponse, StateHistoryLastStateQueryArgs>({
      query(queryArg) {
        const params = new URLSearchParams();

        params.append('vehicle_id', String(queryArg.vehicle_id));
        params.append('timestamp', queryArg.timestamp);

        return `/trip/event-log/state-history/last-state?${params}`;
      },
    }),

    createUpdateStateHistory: build.mutation<CreateUpdateStateHistoryResponse, CreateUpdateStateHistoryRequest>({
      query: (requestData) => ({
        url: '/trip/cycle-state-history/batch',
        body: requestData,
        method: 'POST',
      }),
    }),

    deleteStateHistory: build.mutation<DeleteStateHistoryResponse, DeleteStateHistoryRequest>({
      query: ({ id, confirm }) => ({
        url: `/trip/cycle-state-history/${id}`,
        body: { confirm },
        method: 'DELETE',
      }),
    }),
  }),
});

export const {
  useGetAllStateHistoryQuery,
  useLazyGetAllStateHistoryQuery,
  useGetStateHistoryLastStateQuery,
  useCreateUpdateStateHistoryMutation,
  useDeleteStateHistoryMutation,
} = stateHistoryRtkApi;
