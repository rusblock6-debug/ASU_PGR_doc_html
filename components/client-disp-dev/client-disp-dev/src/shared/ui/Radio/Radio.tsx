import { Radio as MantineRadio, type RadioProps, type RadioGroupProps } from '@mantine/core';

/**
 * Представляет компонент-обертку для компонента радио-кнопки.
 */
function Radio(props: Readonly<RadioProps>) {
  return <MantineRadio {...props} />;
}

/**
 * RadioGroup - обертка для целевого элемента группы радио-кнопок.
 */
export function RadioGroup({ children, ...props }: Readonly<RadioGroupProps>) {
  return <MantineRadio.Group {...props}>{children}</MantineRadio.Group>;
}

const RadioWithComponents = Object.assign(Radio, {
  Group: RadioGroup,
});

export { RadioWithComponents as Radio };
