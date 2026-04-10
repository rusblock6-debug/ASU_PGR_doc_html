import { useDisclosure } from '@mantine/hooks';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { AuthorizationModal } from '@/features/authorization';

import { assertNever } from '@/shared/lib/assert-never';
import { useDocumentTitle } from '@/shared/lib/hooks/useDocumentTitle';
import { getRouteApp, getRouteLearning } from '@/shared/routes/router';

import NIRIcon from '../../assets/svg/nir_icon.svg?react';

import styles from './MainPage.module.css';
import { ServiceButton } from './ServiceButton';

/**
 * Представляет перечисление сервисов.
 */
const SERVICE = {
  DISPATCHING: 'DISPATCHING',
  CLONE: 'CLONE',
  VGOK: 'VGOK',
  LEARNING: 'LEARNING',
  OREM: 'OREM',
  ASODU: 'ASODU',
} as const;

type Service = keyof typeof SERVICE;

/**
 * Представляет компонент главной страницы.
 */
export function MainPage() {
  useDocumentTitle('НАВИГАТОР');

  const [isModalOpen, { close: closeModal }] = useDisclosure(false);
  const [selectedService, setSelectedService] = useState<Service | null>(null);

  const navigate = useNavigate();

  const handleModuleClick = (service: Service) => {
    setSelectedService(service);
    void navigateToService(service);
    // пока отключил авторизацию для демо
    // Временное решение. До тех пока не реализован механизм авторизации.
    // const userLogin = localStorage.getItem('USER_LOGIN');
    // if (
    //   (userLogin && userLogin.length > 0) ||
    //   service === SERVICE.DISPATCHING ||
    //   service === SERVICE.LEARNING ||
    //   service === SERVICE.VGOK ||
    //   service === SERVICE.ASODU ||
    //   service === SERVICE.OREM
    // ) {
    //   navigateToService(service);
    // } else {
    //   openModal();
    // }
  };

  const navigateToService = async (service: Service | null) => {
    if (!service) {
      return null;
    }

    switch (service) {
      case SERVICE.DISPATCHING:
        await navigate(getRouteApp());
        break;
      case SERVICE.CLONE:
        window.open('https://qsimmine12-main.dmi-msk.ru/', '_blank', 'noopener, noreferrer');
        break;
      case SERVICE.VGOK:
        // eslint-disable-next-line sonarjs/no-clear-text-protocols
        window.open('http://10.100.109.30:5173/', '_blank', 'noopener, noreferrer');
        break;
      case SERVICE.OREM:
        window.open(
          'https://www.figma.com/proto/GkmahedFLKCDlPgGS6gKCR/⚡--ОРЭМ?page-id=1581%3A76530&node-id=1612-156440&viewport=111%2C-4%2C0.17&t=BSy9bskhWcIWhRyU-1&scaling=min-zoom&content-scaling=fixed&starting-point-node-id=1612%3A156440/',
          '_blank',
          'noopener, noreferrer',
        );
        break;
      case SERVICE.ASODU:
        window.open(
          'https://www.figma.com/proto/ryU7k5WroqMTZP9aHMNOkE/АСОДУ?page-id=0%3A1&node-id=82-408599&p=f&viewport=-11870%2C-9217%2C0.49&t=727KDvLTe3wOwWLj-1&scaling=min-zoom&content-scaling=fixed&starting-point-node-id=82%3A408599/',
          '_blank',
          'noopener, noreferrer',
        );
        break;
      case SERVICE.LEARNING:
        await navigate(getRouteLearning());
        break;
      default:
        assertNever(service);
    }
  };

  return (
    <div className={styles.root}>
      <div className={styles.content_container}>
        <div className={styles.header}>
          <h1 className={styles.title}>Экосистема цифровых решений</h1>
          <p className={styles.subtitle}>для горнодобывающей промышленности</p>
        </div>
        <div className={styles.buttons_container}>
          <ServiceButton
            variant="pgr"
            handleModuleClick={() => handleModuleClick(SERVICE.DISPATCHING)}
            title="АСУ ПГР"
            description="автоматизированная система управления подземными горными работами"
          />
          <ServiceButton
            variant="clone"
            handleModuleClick={() => handleModuleClick(SERVICE.CLONE)}
            title="Цифровой двойник"
            description="предикативная аналитика горных работ"
          />
          <ServiceButton
            variant="orem"
            handleModuleClick={() => handleModuleClick(SERVICE.OREM)}
            title="ОРЭМ"
            description="система оптимизации оптовых закупок энергоресурсов"
          />
          <ServiceButton
            variant="asodu"
            handleModuleClick={() => handleModuleClick(SERVICE.ASODU)}
            title="АСОДУ"
            description="система оперативного диспетчерского управления энергоресурсами"
          />
          <ServiceButton
            variant="vgok"
            handleModuleClick={() => handleModuleClick(SERVICE.VGOK)}
            title="Контроль ПНР ВГОК"
            description="система контроля за пуско-наладочными работами горнообогатительного комбината"
          />
          <ServiceButton
            variant="learning"
            handleModuleClick={() => handleModuleClick(SERVICE.LEARNING)}
            title="Обучение"
            description="модуль по обучению работе с продуктами"
          />
        </div>
        <div className={styles.footer}>
          <div className={styles.logo_container}>
            <NIRIcon className={styles.logo_first} />
          </div>
          <div className={styles.contact_container}>
            <p className={styles.contact_title}>Для связи</p>
            <a
              className={styles.mail}
              href="mailto:support@nir.center"
            >
              support@nir.center
            </a>
          </div>
        </div>
      </div>
      <AuthorizationModal
        isOpen={isModalOpen}
        onClose={closeModal}
        onConfirm={() => navigateToService(selectedService)}
      />
    </div>
  );
}
