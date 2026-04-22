import { nanoid } from '@reduxjs/toolkit';
import { useState } from 'react';

import type { PolylinePoint } from './types';

/**
 * Хук для управления массивом точек полилинии (для рисования линейки).
 */
export function usePolylineDrawing() {
  const [points, setPoints] = useState<readonly PolylinePoint[]>([]);

  const addPoint = (x: number, z: number) => {
    setPoints((prev) => [...prev, { id: nanoid(), x, z }]);
  };

  const insertPoint = (index: number, x: number, z: number) => {
    const id = nanoid();
    setPoints((prev) => [...prev.slice(0, index), { id, x, z }, ...prev.slice(index)]);
    return id;
  };

  const movePoint = (id: string, x: number, z: number) => {
    setPoints((prev) => prev.map((point) => (point.id === id ? { ...point, x, z } : point)));
  };

  const removePoint = (id: string) => {
    setPoints((prev) => {
      return prev.filter((point) => point.id !== id);
    });
  };

  return { points, addPoint, insertPoint, movePoint, removePoint };
}
