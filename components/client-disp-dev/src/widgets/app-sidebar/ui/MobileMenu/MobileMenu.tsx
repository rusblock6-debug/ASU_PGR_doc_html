import { Link } from 'react-router-dom';

import { type NavLinks } from '@/shared/routes/navigation';
import { getRouteMain } from '@/shared/routes/router';

import { useSidebar } from '../../model/useSidebar';
import { NavMain } from '../NavMain';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../Sheet';

import styles from './MenuMobile.module.css';

/**
 * Свойства компонента мобильного меню.
 */
interface MobileMenuProps {
  /** Элементы меню. */
  readonly items: readonly NavLinks[];
}

/**
 * Мобильное меню.
 */
export function MobileMenu({ items }: MobileMenuProps) {
  const { open, setOpen, selectedSectionIndex } = useSidebar();

  return (
    <Sheet
      open={open}
      onOpenChange={setOpen}
    >
      <SheetContent
        className={styles.sheet_content}
        side="left"
      >
        <SheetHeader className="g-screen-reader-only">
          <SheetTitle>Меню приложения</SheetTitle>
          <SheetDescription>Отображает навигацию</SheetDescription>
        </SheetHeader>
        <div className={styles.mobile_header}>
          <Link
            tabIndex={-1}
            className={styles.mobile_header_link}
            to={getRouteMain()}
          >
            <span className={styles.mobile_logo}>{`навигатор.\u00A0пгр`}</span>
          </Link>
        </div>

        <NavMain
          items={items}
          selectedSectionIndex={selectedSectionIndex}
          onNavigate={() => setOpen(false)}
        />
      </SheetContent>
    </Sheet>
  );
}
