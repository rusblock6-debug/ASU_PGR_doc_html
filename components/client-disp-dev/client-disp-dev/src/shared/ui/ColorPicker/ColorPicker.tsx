import { ColorPicker as MantineColorPicker, type ColorPickerProps as MantineColorPickerProps } from '@mantine/core';

/**
 * Адаптер над Mantine ColorPicker — панель выбора цвета без текстового инпута.
 * https://mantine.dev/core/color-picker/
 */
export function ColorPicker({ format = 'hex', size = 'sm', ...props }: Readonly<MantineColorPickerProps>) {
  return (
    <MantineColorPicker
      {...props}
      format={format}
      size={size}
    />
  );
}
