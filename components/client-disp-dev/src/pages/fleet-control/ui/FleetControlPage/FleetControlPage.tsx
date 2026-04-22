import { Header, Page } from '@/widgets/page-layout';

import { AppRoutes } from '@/shared/routes/router';

import { FleetControlPageContextProvider } from '../../model/FleetControlPageContext';
import { FleetControl } from '../FleetControl';
import { Toolbar } from '../Toolbar';

import styles from './FleetControlPage.module.css';

/**
 * Представляет компонент страницы "Управление техникой".
 */
export function FleetControlPage() {
  return (
    <FleetControlPageContextProvider>
      <Page className={styles.root}>
        <Header
          routeKey={AppRoutes.FLEET_CONTROL}
          headerClassName={styles.header}
        >
          <Toolbar />
        </Header>
        <FleetControl />
      </Page>
    </FleetControlPageContextProvider>
  );
}
