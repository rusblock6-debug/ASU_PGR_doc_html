import { Header, Page } from '@/widgets/page-layout';

import { AppRoutes } from '@/shared/routes/router';

export function MapPage() {
  /* eslint-disable sonarjs/no-clear-text-protocols */
  return (
    <Page>
      <Header routeKey={AppRoutes.MAP} />
      <iframe
        src="http://10.100.109.14:3003/"
        className="iframe-full-size"
        title="Карта"
      />
    </Page>
  );
}
