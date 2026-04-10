import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import * as React from 'react';

import styles from './Button.module.css';

const buttonVariants = cva([styles.button, styles.size], {
  variants: {
    variant: {
      primary: styles.variant_primary,
      clear: styles.variant_clear,
      sidebar: styles.variant_sidebar,
      header: styles.variant_header,
    },
    size: {
      '2xl': styles.size_xxl,
      xl: styles.size_xl,
      large: styles.size_l,
      medium: styles.size_m,
      small: styles.size_s,
      'extra-small': styles.size_xs,
      full: styles.size_full,
    },
  },
  defaultVariants: {
    variant: 'primary',
  },
});

export function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & {
    readonly asChild?: boolean;
  }) {
  const Comp = asChild ? Slot : 'button';

  return (
    <Comp
      className={buttonVariants({ variant, size, className })}
      {...props}
    />
  );
}
