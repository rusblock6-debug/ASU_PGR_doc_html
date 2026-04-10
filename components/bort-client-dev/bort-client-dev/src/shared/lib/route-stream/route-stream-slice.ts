import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

import type { RouteStreamPartialUpdate } from '@/shared/lib/route-stream/parse-route-stream-payload';

/** Состояние Redux: метрики маршрута из SSE (дистанция, ETA). */
interface RouteStreamState {
  distanceMeters: number | null;
  durationSeconds: number | null;
}

const initialState: RouteStreamState = {
  distanceMeters: null,
  durationSeconds: null,
};

export const routeStreamSlice = createSlice({
  name: 'routeStream',
  initialState,
  reducers: {
    routeStreamUpdateReceived(state, action: PayloadAction<RouteStreamPartialUpdate>) {
      if (action.payload.distanceMeters !== undefined) {
        state.distanceMeters = action.payload.distanceMeters;
      }
      if (action.payload.durationSeconds !== undefined) {
        state.durationSeconds = action.payload.durationSeconds;
      }
    },
  },
});

export const { routeStreamUpdateReceived } = routeStreamSlice.actions;

export const selectRouteStreamDistanceMeters = (state: RootState) => state.routeStream.distanceMeters;
export const selectRouteStreamDurationSeconds = (state: RootState) => state.routeStream.durationSeconds;
