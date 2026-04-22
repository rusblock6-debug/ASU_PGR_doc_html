import { useSubscribeShiftTasksStreamQuery } from '@/shared/api/endpoints/shift-tasks';

/** Подписка на SSE наряд-заданий через RTK Query streaming endpoint. */
export const useShiftTasksSse = () => {
  useSubscribeShiftTasksStreamQuery();
};
