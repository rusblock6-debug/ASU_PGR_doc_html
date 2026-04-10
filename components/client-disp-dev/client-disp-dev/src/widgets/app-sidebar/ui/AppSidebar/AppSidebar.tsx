import { cn } from '@/shared/lib/classnames-utils';
import { navLinks } from '@/shared/routes/navigation';
import { Button } from '@/shared/ui/Button';

import { SidebarProvider } from '../../model/SidebarProvider';
import { useSidebar } from '../../model/useSidebar';
import { MobileMenu } from '../MobileMenu';
import { SidebarTrigger } from '../SidebarTrigger';

import styles from './AppSidebar.module.css';

export function AppSidebar() {
  return (
    <SidebarProvider>
      <AppSidebarContent />
    </SidebarProvider>
  );
}

function AppSidebarContent() {
  const { openSidebarWithSection } = useSidebar();

  return (
    <>
      <div className={cn(styles.sidebar)}>
        <div className={styles.sidebar_gap} />
        <div className={styles.sidebar_inner}>
          <div className={styles.sidebar_header}>
            <SidebarTrigger />
          </div>

          <div className={styles.sidebar_content}>
            {navLinks.map((item, index) => (
              <li
                key={item.title + index}
                className={styles.menu_item}
              >
                <Button
                  variant="sidebar"
                  onClick={() => openSidebarWithSection(index)}
                >
                  {item.icon && <item.icon />}
                </Button>
              </li>
            ))}
          </div>
        </div>
      </div>

      <MobileMenu items={navLinks} />
    </>
  );
}
