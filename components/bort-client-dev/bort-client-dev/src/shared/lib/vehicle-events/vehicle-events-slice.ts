import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

import type { LocationEvent, StateEvent, VehicleState, WeightEvent } from '@/shared/api/types/vehicle-events';

/** Состояние Redux: последние события борта из SSE (статус, место/тег, вес). */
interface VehicleEventsState {
  stateStatus: VehicleState | null;
  stateChangedAt: string | null;
  locationPlaceName: string | null;
  locationTagName: string | null;
  weightValue: number | null;
}

const initialState: VehicleEventsState = {
  stateStatus: null,
  stateChangedAt: null,
  locationPlaceName: null,
  locationTagName: null,
  weightValue: null,
};

export const vehicleEventsSlice = createSlice({
  name: 'vehicleEvents',
  initialState,
  reducers: {
    stateEventReceived(state, action: PayloadAction<StateEvent>) {
      state.stateStatus = action.payload.status;
      state.stateChangedAt = action.payload.timestamp;
    },
    locationEventReceived(state, action: PayloadAction<LocationEvent>) {
      state.locationPlaceName = action.payload.place_name;
      state.locationTagName = action.payload.tag_name;
    },
    weightEventReceived(state, action: PayloadAction<WeightEvent>) {
      state.weightValue = action.payload.value;
    },
  },
});

export const { stateEventReceived, locationEventReceived, weightEventReceived } = vehicleEventsSlice.actions;

export const selectVehicleState = (state: RootState) => state.vehicleEvents.stateStatus;
export const selectStateChangedAt = (state: RootState) => state.vehicleEvents.stateChangedAt;
export const selectLocationPlaceName = (state: RootState) => state.vehicleEvents.locationPlaceName;
export const selectLocationTagName = (state: RootState) => state.vehicleEvents.locationTagName;
export const selectWeightValue = (state: RootState) => state.vehicleEvents.weightValue;
