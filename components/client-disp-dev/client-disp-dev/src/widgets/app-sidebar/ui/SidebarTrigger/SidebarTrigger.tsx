import MenuIcon from '@/shared/assets/icons/ic-burger.svg?react';
import { Button } from '@/shared/ui/Button';

import { useSidebar } from '../../model/useSidebar';

import styles from './SidebarTrigger.module.css';

export function SidebarTrigger() {
  const { toggleSidebar } = useSidebar();

  const handleClick = () => {
    toggleSidebar();
  };

  return (
    <Button
      variant="sidebar"
      className={styles.sidebar_trigger}
      onClick={handleClick}
    >
      <MenuIcon />
      <span className="g-screen-reader-only">Открыть/закрыть меню</span>
    </Button>
  );
}
