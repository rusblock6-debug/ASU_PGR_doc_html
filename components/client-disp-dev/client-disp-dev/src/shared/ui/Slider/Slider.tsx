import { Slider as MantineSlider, type SliderProps as MantineSliderProps } from '@mantine/core';

type SliderProps = Readonly<MantineSliderProps>;

/**
 * Адаптер над Mantine Slider, чтобы скрыть внешнюю зависимость от Mantine в UI-слое.
 */
export function Slider(props: SliderProps) {
  return <MantineSlider {...props} />;
}
