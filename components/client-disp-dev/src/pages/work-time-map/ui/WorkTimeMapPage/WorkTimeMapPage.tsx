import { Header, Page } from '@/widgets/page-layout';

import { AppRoutes } from '@/shared/routes/router';

import { WorkTimeMapPageContextProvider } from '../../model/WorkTimeMapPageContext';
import { Toolbar } from '../Toolbar';
import { WorkTimeMapContainer } from '../WorkTimeMapContainer';

import styles from './WorkTimeMapPage.module.css';

/**
 * Представляет компонент страницы "Карта рабочего времени".
 */
export function WorkTimeMapPage() {
  return (
    <WorkTimeMapPageContextProvider>
      <Page className={styles.root}>
        <Header
          routeKey={AppRoutes.WORK_TIME_MAP}
          headerClassName={styles.header}
        >
          <Toolbar />
        </Header>
        <WorkTimeMapContainer />
      </Page>
    </WorkTimeMapPageContextProvider>
  );
}
