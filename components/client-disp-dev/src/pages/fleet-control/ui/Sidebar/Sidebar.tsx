import Icon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { AppButton } from '@/shared/ui/AppButton';

import { useFleetControlPageContext } from '../../model/FleetControlPageContext';
import { Divider } from '../Divider';

import { ResultsByCargoType } from './ResultsByCargoType';
import styles from './Sidebar.module.css';
import { UnusedTechnique } from './UnusedTechnique';

/**
 * Представляет компонент правой панели на странице "Управление техникой".
 */
export function Sidebar() {
  const { isOpenSidebar, handleChangeOpenSidebar } = useFleetControlPageContext();

  return (
    <div className={cn(styles.root, { [styles.close]: !isOpenSidebar })}>
      {isOpenSidebar && (
        <AppButton
          size="xs"
          onlyIcon
          className={styles.button}
          onClick={() => handleChangeOpenSidebar(false)}
        >
          <Icon className={styles.icon} />
        </AppButton>
      )}
      <ResultsByCargoType />
      <Divider
        height={!isOpenSidebar ? 1 : undefined}
        color={!isOpenSidebar ? 'var(--bg-widget-hover)' : undefined}
      />
      <UnusedTechnique />
    </div>
  );
}
