import { Header, Page } from '@/widgets/page-layout';

import { AppRoutes } from '@/shared/routes/router';

export function SettingsPage() {
  return (
    <Page>
      <Header routeKey={AppRoutes.SETTINGS} />

      <p>Settings Page</p>
    </Page>
  );
}
