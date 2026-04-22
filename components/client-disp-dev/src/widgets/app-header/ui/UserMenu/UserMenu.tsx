import React from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { selectUser, useLogout } from '@/entities/user';

import ChevronIcon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import ProfileIcon from '@/shared/assets/icons/ic-profile-fill.svg?react';
import { useConfirm } from '@/shared/lib/confirm';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { getRouteMain } from '@/shared/routes/router';
import { Button } from '@/shared/ui/Button';
import { Menu } from '@/shared/ui/Menu';

import styles from './UserMenu.module.css';

/**
 * Меню пользователя в шапке (профиль/выход).
 */
export function UserMenu() {
  const navigate = useNavigate();
  const confirm = useConfirm();
  const user = useAppSelector(selectUser);
  const { logout } = useLogout();

  const handleExitClick = async (e: React.MouseEvent) => {
    e.preventDefault();

    const confirmed = await confirm({
      title: 'Вы действительно хотите выйти?',
      confirmText: 'Выйти',
    });

    if (confirmed) {
      await logout();
      await navigate(getRouteMain());
    }
  };

  return (
    <Menu width={149}>
      <Menu.Target>
        <Button
          variant="clear"
          className={styles.profile_button}
        >
          <p className={styles.profile_text}>
            <ProfileIcon
              width={16}
              height={16}
            />
            <span>{user?.username ?? 'Пользователь'}</span>
            <ChevronIcon className={styles.chevron_icon} />
          </p>
        </Button>
      </Menu.Target>

      <Menu.Dropdown>
        <Menu.Item style={{ padding: 0 }}>
          <Link
            className={styles.link}
            to={getRouteMain()}
            onClick={handleExitClick}
          >
            Выйти
          </Link>
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}
