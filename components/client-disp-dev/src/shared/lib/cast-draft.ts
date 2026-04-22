import type { Draft } from '@reduxjs/toolkit';

/**
 * Приводит значение к типу {@link Draft}, чтобы безопасно использовать
 * иммутабельные данные внутри RTK-редьюсеров (Immer).
 *
 * Не выполняет никаких преобразований в рантайме — только type-cast.
 */
export const castDraft = <T>(value: T): Draft<T> => value as Draft<T>;
