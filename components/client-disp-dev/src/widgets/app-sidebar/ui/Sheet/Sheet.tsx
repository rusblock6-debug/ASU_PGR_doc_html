import * as SheetPrimitive from '@radix-ui/react-dialog';
import * as React from 'react';

import CrossIcon from '@/shared/assets/icons/ic-cross.svg?react';
import { createBoundClassNames } from '@/shared/lib/classnames-utils';

import styles from './Sheet.module.css';

const cx = createBoundClassNames(styles);

function Sheet({ ...props }: Readonly<React.ComponentProps<typeof SheetPrimitive.Root>>) {
  return (
    <SheetPrimitive.Root
      data-slot="sheet"
      {...props}
    />
  );
}

function SheetTrigger({ ...props }: React.ComponentProps<typeof SheetPrimitive.Trigger>) {
  return (
    <SheetPrimitive.Trigger
      data-slot="sheet-trigger"
      {...props}
    />
  );
}

function SheetClose({ ...props }: React.ComponentProps<typeof SheetPrimitive.Close>) {
  return (
    <SheetPrimitive.Close
      data-slot="sheet-close"
      {...props}
    />
  );
}

function SheetPortal({ ...props }: Readonly<React.ComponentProps<typeof SheetPrimitive.Portal>>) {
  return (
    <SheetPrimitive.Portal
      data-slot="sheet-portal"
      {...props}
    />
  );
}

function SheetOverlay({ className, ...props }: React.ComponentProps<typeof SheetPrimitive.Overlay>) {
  return (
    <SheetPrimitive.Overlay
      data-slot="sheet-overlay"
      className={cx(styles.sheet_overlay, className)}
      {...props}
    />
  );
}

function SheetContent({
  className,
  children,
  side = 'right',
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Content> & {
  readonly side?: 'top' | 'right' | 'bottom' | 'left';
}) {
  const getSideClass = () => {
    switch (side) {
      case 'right':
        return styles.sheet_content_right;
      case 'left':
        return styles.sheet_content_left;
      case 'top':
        return styles.sheet_content_top;
      case 'bottom':
        return styles.sheet_content_bottom;
      default:
        return styles.sheet_content_right;
    }
  };

  return (
    <SheetPortal>
      <SheetOverlay />
      <SheetPrimitive.Content
        data-slot="sheet-content"
        className={cx(styles.sheet_content, getSideClass(), className)}
        {...props}
      >
        {children}
        <SheetPrimitive.Close className={styles.sheet_close}>
          <CrossIcon className={styles.close_icon} />
          <span className="g-screen-reader-only">Закрыть</span>
        </SheetPrimitive.Close>
      </SheetPrimitive.Content>
    </SheetPortal>
  );
}

function SheetHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="sheet-header"
      className={cx(styles.sheet_header, className)}
      {...props}
    />
  );
}

function SheetFooter({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="sheet-footer"
      className={cx(styles.sheet_footer, className)}
      {...props}
    />
  );
}

function SheetTitle({ className, ...props }: React.ComponentProps<typeof SheetPrimitive.Title>) {
  return (
    <SheetPrimitive.Title
      data-slot="sheet-title"
      className={cx(styles.sheet_title, className)}
      {...props}
    />
  );
}

function SheetDescription({ className, ...props }: React.ComponentProps<typeof SheetPrimitive.Description>) {
  return (
    <SheetPrimitive.Description
      data-slot="sheet-description"
      className={cx(styles.sheet_description, className)}
      {...props}
    />
  );
}

export { Sheet, SheetTrigger, SheetClose, SheetContent, SheetHeader, SheetFooter, SheetTitle, SheetDescription };
