import { rtkApi } from '@/shared/api';

import type { MoveVehicleRequest } from './types';

export const locationsRtkApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    moveVehicle: builder.mutation<null, MoveVehicleRequest>({
      query: (body) => ({
        url: '/graph/location/move_vehicle',
        method: 'POST',
        body,
      }),
    }),
  }),
});

export const { useMoveVehicleMutation } = locationsRtkApi;
