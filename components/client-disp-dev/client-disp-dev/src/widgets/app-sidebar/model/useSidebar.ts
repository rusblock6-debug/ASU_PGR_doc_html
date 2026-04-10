import { createContext, useContext } from 'react';

export interface SidebarContextProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  selectedSectionIndex: number | null;
  openSidebarWithSection: (index: number) => void;
}

export const SidebarContext = createContext<SidebarContextProps | null>(null);

export function useSidebar() {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error('useSidebar must be used within a SidebarProvider.');
  }
  return context;
}
