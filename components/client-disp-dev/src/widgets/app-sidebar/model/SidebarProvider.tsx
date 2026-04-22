import * as React from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { SidebarContext, type SidebarContextProps } from './useSidebar';

const SIDEBAR_KEYBOARD_SHORTCUT = ['b', 'и'];

export function SidebarProvider({ children }: React.ComponentProps<'div'>) {
  const [open, setOpen] = useState(false);
  const [selectedSectionIndex, setSelectedSectionIndex] = useState<number | null>(null);

  const toggleSidebar = useCallback(() => {
    setOpen((prev) => !prev);
    setSelectedSectionIndex(null);
  }, [setOpen]);

  const openSidebarWithSection = useCallback(
    (index: number) => {
      setSelectedSectionIndex(index);
      setOpen(true);
    },
    [setOpen],
  );

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // ctrl + b, ctrl + и
      if (SIDEBAR_KEYBOARD_SHORTCUT.includes(event.key) && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        toggleSidebar();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleSidebar]);

  const contextValue = useMemo<SidebarContextProps>(
    () => ({
      open,
      setOpen,
      toggleSidebar,
      selectedSectionIndex,
      openSidebarWithSection,
    }),
    [open, setOpen, toggleSidebar, selectedSectionIndex, openSidebarWithSection],
  );

  return <SidebarContext.Provider value={contextValue}>{children}</SidebarContext.Provider>;
}
