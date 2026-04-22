import { Link, NavLink } from 'react-router-dom';

import HomeIcon from '@/shared/assets/icons/ic-home.svg?react';
import MenuIcon from '@/shared/assets/icons/ic-menu-fill.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { getRouteApp, getRouteMain, getRouteWorkspace } from '@/shared/routes/router';

import { Status } from '../Status';
import { UserMenu } from '../UserMenu';

import styles from './AppHeader.module.css';

export function AppHeader() {
  return (
    <header className={styles.header}>
      <div className={styles.header_content}>
        <Link
          tabIndex={-1}
          className={styles.app_header_link}
          to={getRouteMain()}
        >
          <span className={styles.logo_icon}>{`навигатор.\u00A0пгр`}</span>
        </Link>

        <NavLink
          to={getRouteApp()}
          end
          className={({ isActive }) => cn(styles.nav_link, { [styles.nav_link_active]: isActive })}
        >
          <HomeIcon />
        </NavLink>

        <NavLink
          to={getRouteWorkspace()}
          className={({ isActive }) => cn(styles.nav_link, { [styles.nav_link_active]: isActive })}
        >
          <MenuIcon />
        </NavLink>
      </div>

      <div className={styles.right_section}>
        <Status />
        <UserMenu />
      </div>
    </header>
  );
}
