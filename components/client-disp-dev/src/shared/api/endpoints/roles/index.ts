export type { Role, RolesResponse, CreateRoleRequest, UpdateRoleRequest } from './types';
export {
  useGetAllRolesQuery,
  useGetRolesInfiniteQuery,
  useGetRoleByIdQuery,
  useCreateRoleMutation,
  useUpdateRoleMutation,
  useDeleteRoleMutation,
} from './roles-rtk';
