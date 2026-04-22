import moment from 'moment/moment';
import { type RefObject, useEffect, useMemo } from 'react';
import type { DataSet } from 'vis-data';
import type { Timeline } from 'vis-timeline/standalone';

import type { TimelineItemExtended } from '../types/timeline-item-extended';
import type { TimelineZoomControl } from '../types/timeline-zoom-control';

/**
 * Представляет хук для управления масштабом таймлайна.
 *
 * @param itemsRef ссылка на список элементов.
 * @param timelineInstanceRef ссылка на таймлайн.
 * @param zoomControlsRef ссылка на набор методов для управления масштабом таймлайна.
 */
export function useZoomControl(
  itemsRef: RefObject<DataSet<TimelineItemExtended>>,
  timelineInstanceRef?: RefObject<Timeline | null>,
  zoomControlsRef?: RefObject<TimelineZoomControl | null>,
) {
  const zoomControls: TimelineZoomControl = useMemo(
    () => ({
      zoomIn: (amount = 1.2) => {
        if (!timelineInstanceRef?.current) return;
        const range = timelineInstanceRef.current.getWindow();
        const center = (range.start.getTime() + range.end.getTime()) / 2;
        const newRange = (range.end.getTime() - range.start.getTime()) / amount;

        timelineInstanceRef.current.setWindow(center - newRange / 2, center + newRange / 2);
      },

      zoomOut: (amount = 1.2) => {
        if (!timelineInstanceRef?.current) return;
        const range = timelineInstanceRef.current.getWindow();
        const center = (range.start.getTime() + range.end.getTime()) / 2;
        const newRange = (range.end.getTime() - range.start.getTime()) * amount;

        timelineInstanceRef.current.setWindow(center - newRange / 2, center + newRange / 2);
      },

      zoomToFit: () => {
        if (!timelineInstanceRef?.current) return;

        const items = itemsRef.current.get();
        if (items.length === 0) return;

        const minStart = Math.min(...items.map((i) => i.start as number));
        const maxEnd = Math.max(...items.map((i) => i.end as number));

        const padding = (maxEnd - minStart) * 0.1;

        timelineInstanceRef.current.setWindow(minStart - padding, maxEnd + padding);
      },

      zoomToRange: (start: Date, end: Date) => {
        if (!timelineInstanceRef?.current) return;

        const startMs = start.getTime();
        const endMs = end.getTime();

        timelineInstanceRef.current.setWindow(startMs, endMs, { animation: true });
      },

      setZoom: (zoomLevel: number) => {
        if (!timelineInstanceRef?.current) return;

        const range = timelineInstanceRef.current.getWindow();
        const center = (range.start.getTime() + range.end.getTime()) / 2;

        timelineInstanceRef.current.setWindow(center - zoomLevel / 2, center + zoomLevel / 2);
      },

      getCurrentZoom: () => {
        if (!timelineInstanceRef?.current) return 0;
        const range = timelineInstanceRef.current.getWindow();
        return range.end.getTime() - range.start.getTime();
      },

      goToNow: () => {
        if (!timelineInstanceRef?.current) return;

        const now = moment().utcOffset('+0300').valueOf();
        const currentZoom = zoomControls.getCurrentZoom();

        timelineInstanceRef.current.setWindow(now - currentZoom / 2, now + currentZoom / 2);
      },

      goToDate: (date: Date) => {
        if (!timelineInstanceRef?.current) return;

        const timestamp = moment(date).utcOffset('+0300').valueOf();
        const currentZoom = zoomControls.getCurrentZoom();

        timelineInstanceRef.current.setWindow(timestamp - currentZoom / 2, timestamp + currentZoom / 2);
      },
    }),
    [itemsRef, timelineInstanceRef],
  );

  useEffect(() => {
    if (zoomControlsRef) {
      zoomControlsRef.current = zoomControls;
    }
  }, [zoomControls, zoomControlsRef]);
}
