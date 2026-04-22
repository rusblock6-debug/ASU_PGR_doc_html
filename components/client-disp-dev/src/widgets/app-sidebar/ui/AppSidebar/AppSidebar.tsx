import { cn } from '@/shared/lib/classnames-utils';
import { Button } from '@/shared/ui/Button';

import { SidebarProvider } from '../../model/SidebarProvider';
import { useFilteredNavLinks } from '../../model/useFilteredNavLinks';
import { useSidebar } from '../../model/useSidebar';
import { MobileMenu } from '../MobileMenu';
import { SidebarTrigger } from '../SidebarTrigger';

import styles from './AppSidebar.module.css';

/** Сайдбар приложения с десктопным и мобильным меню. */
export function AppSidebar() {
  return (
    <SidebarProvider>
      <AppSidebarContent />
    </SidebarProvider>
  );
}

/** Контент сайдбара: иконки разделов и мобильное меню. */
function AppSidebarContent() {
  const { openSidebarWithSection } = useSidebar();
  const filteredNavLinks = useFilteredNavLinks();

  return (
    <>
      <div className={cn(styles.sidebar)}>
        <div className={styles.sidebar_gap} />
        <div className={styles.sidebar_inner}>
          <div className={styles.sidebar_header}>
            <SidebarTrigger />
          </div>

          <div className={styles.sidebar_content}>
            {filteredNavLinks.map((item, index) => (
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

      <MobileMenu items={filteredNavLinks} />
    </>
  );
}
