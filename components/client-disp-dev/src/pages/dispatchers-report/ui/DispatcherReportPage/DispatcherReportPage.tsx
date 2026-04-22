import { Header, Page } from '@/widgets/page-layout';

import { AppRoutes } from '@/shared/routes/router';

export function DispatcherReportPage() {
  return (
    <Page>
      <Header routeKey={AppRoutes.DISPATCHERS_REPORT} />

      <p>
        <b>Оперативная работа → Рапорт диспетчера</b> <br />
        Lorem ipsum dolor sit amet, consectetur adipisicing elit. Ab adipisci culpa cumque dignissimos dolore esse,
        eveniet facere facilis impedit maxime non numquam qui ratione repudiandae sapiente sit sunt veniam voluptas?
        Lorem ipsum dolor sit amet, consectetur adipisicing elit. Dicta dolor maxime minus. Ad aperiam aut consequatur
        doloribus est facilis hic in laborum maxime molestias necessitatibus perferendis, repudiandae sapiente,
        temporibus, vel? lorem Lorem ipsum dolor sit amet, consectetur adipisicing elit. Ab adipisci culpa cumque
        dignissimos dolore esse, eveniet facere facilis impedit maxime non numquam qui ratione repudiandae sapiente sit
        sunt veniam voluptas?
      </p>
    </Page>
  );
}
