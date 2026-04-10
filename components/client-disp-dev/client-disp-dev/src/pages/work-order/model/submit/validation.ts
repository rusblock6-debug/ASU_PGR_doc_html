import type { ShiftTask } from '@/shared/api/endpoints/shift-tasks';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValueNotEmpty } from '@/shared/lib/has-value';

import { BlockReason } from '../block-reasons';
import { REQUIRED_FIELDS } from '../constants';
import type { TaskBlockState, WorkOrderEdits } from '../types';
import { mergeVehicleTasks } from '../utils';

/**
 * Валидирует только изменённые задачи (`created` + `modified`).
 */
export function validateChangedTasks(
  edits: WorkOrderEdits,
  shiftTasks: readonly ShiftTask[],
  vehicleIds: readonly number[],
) {
  const shiftTaskMap = new Map(shiftTasks.map((shiftTask) => [shiftTask.vehicle_id, shiftTask]));
  const errors: Record<string, TaskBlockState> = {};
  const invalidVehicleIds = new Set<number>();

  for (const vehicleId of vehicleIds) {
    const serverRouteTasks = shiftTaskMap.get(vehicleId)?.route_tasks ?? EMPTY_ARRAY;

    const allTasks = mergeVehicleTasks(
      serverRouteTasks,
      edits.created[vehicleId],
      edits.modified[vehicleId],
      edits.deleted[vehicleId],
    );

    const changedIds = new Set([
      ...Object.keys(edits.created[vehicleId] ?? {}),
      ...Object.keys(edits.modified[vehicleId] ?? {}),
    ]);

    for (const task of allTasks) {
      if (!changedIds.has(task.id)) continue;

      const emptyFields = REQUIRED_FIELDS.filter((field) => !hasValueNotEmpty(task[field]));
      if (emptyFields.length > 0) {
        errors[task.id] = { reason: BlockReason.REQUIRED_FIELDS, errorFields: emptyFields };
        invalidVehicleIds.add(vehicleId);
      }
    }
  }

  return { errors, invalidVehicleIds };
}
