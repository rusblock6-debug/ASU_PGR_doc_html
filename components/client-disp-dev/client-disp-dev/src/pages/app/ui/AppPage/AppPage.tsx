import { NavMain } from '@/widgets/app-sidebar';
import { Page } from '@/widgets/page-layout';

import { Favorites } from '@/features/favorite-page';

import { navLinks } from '@/shared/routes/navigation';

import styles from './AppPage.module.css';

export function AppPage() {
  return (
    <Page className={styles.home_page}>
      <div className={styles.favorites}>
        <h2 className={styles.heading}>Избранное</h2>
        <Favorites />
      </div>

      <div>
        <h2 className={styles.heading}>Разделы</h2>
        <NavMain
          items={navLinks}
          variant="block"
        />
      </div>
    </Page>
  );
}
