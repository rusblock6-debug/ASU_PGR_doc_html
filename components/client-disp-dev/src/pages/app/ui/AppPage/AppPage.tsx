import { NavMain, useFilteredNavLinks } from '@/widgets/app-sidebar';
import { Page } from '@/widgets/page-layout';

import { Favorites } from '@/features/favorite-page';

import styles from './AppPage.module.css';

export function AppPage() {
  const filteredNavLinks = useFilteredNavLinks();

  return (
    <Page className={styles.home_page}>
      <div className={styles.favorites}>
        <h2 className={styles.heading}>Избранное</h2>
        <Favorites />
      </div>

      <div>
        <h2 className={styles.heading}>Разделы</h2>
        <NavMain
          items={filteredNavLinks}
          variant="block"
        />
      </div>
    </Page>
  );
}
