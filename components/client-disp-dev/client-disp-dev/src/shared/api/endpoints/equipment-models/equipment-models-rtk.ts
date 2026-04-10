import { rtkApi } from '@/shared/api';

import type {
  UpdateEquipmentModelParams,
  EquipmentModel,
  CreateEquipmentModelRequest,
  EquipmentModelsApiResponse,
  EquipmentModelsQueryArg,
} from './types';

export const equipmentModelsRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getAllEquipmentModels: build.query<readonly EquipmentModel[], EquipmentModelsQueryArg | void>({
      query(queryArg) {
        const params = new URLSearchParams();

        if (queryArg?.consist) {
          params.append('consist', queryArg.consist);
        }

        const query = params.toString();
        return query ? `/vehicle-models?${query}` : '/vehicle-models';
      },

      transformResponse: (response: EquipmentModelsApiResponse) => response.items,

      providesTags: ['Equipment'],
    }),

    createEquipmentModel: build.mutation<EquipmentModel, CreateEquipmentModelRequest>({
      query: (body) => ({
        url: '/vehicle-models',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Equipment'],
    }),

    updateEquipmentModel: build.mutation<EquipmentModel, UpdateEquipmentModelParams>({
      query: ({ id, body }) => ({
        url: `/vehicle-models/${id}`,
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['Equipment'],
    }),

    deleteEquipmentModel: build.mutation<void, number>({
      query: (id) => ({
        url: `/vehicle-models/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Equipment'],
    }),
  }),
});

export const {
  useGetAllEquipmentModelsQuery,
  useCreateEquipmentModelMutation,
  useUpdateEquipmentModelMutation,
  useDeleteEquipmentModelMutation,
} = equipmentModelsRtkApi;
