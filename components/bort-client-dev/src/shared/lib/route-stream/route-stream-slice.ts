import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

import type { RouteStreamPartialUpdate } from '@/shared/lib/route-stream/parse-route-stream-payload';

/** Состояние Redux: метрики маршрута из SSE (дистанция, ETA, прогресс). */
interface RouteStreamState {
  distanceMeters: number | null;
  durationSeconds: number | null;
  progressPercent: number | null;
}

const initialState: RouteStreamState = {
  distanceMeters: null,
  durationSeconds: null,
  progressPercent: null,
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
    routeProgressReceived(state, action: PayloadAction<number>) {
      state.progressPercent = action.payload;
    },
  },
});

export const { routeStreamUpdateReceived, routeProgressReceived } = routeStreamSlice.actions;

export const selectRouteStreamDistanceMeters = (state: RootState) => state.routeStream.distanceMeters;
export const selectRouteStreamDurationSeconds = (state: RootState) => state.routeStream.durationSeconds;
export const selectRouteProgressPercent = (state: RootState) => state.routeStream.progressPercent;
