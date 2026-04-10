import { Alert as MantineAlert, type AlertProps as MantineAlertProps } from '@mantine/core';

/**
 * Представляет компонент алерта. https://mantine.dev/core/alert/
 */
export function Alert(props: Readonly<MantineAlertProps>) {
  return <MantineAlert {...props} />;
}
