import { Link } from 'react-router-dom';

import { cn } from '@/shared/lib/classnames-utils';
import { getTitleById } from '@/shared/routes/get-title-by-id';
import { getItemAndSectionByPageKey } from '@/shared/routes/navigation';
import { getRouteByKey } from '@/shared/routes/router';

import { useFavoritePages } from '../../model/FavoritePagesContext';
import { FavoriteButton } from '../FavoriteButton';

import styles from './Favorites.module.css';

export function Favorites() {
  const { favoritePages } = useFavoritePages();

  if (!favoritePages.length) {
    return <p className={styles.text}>Избранных страниц пока нет</p>;
  }

  return (
    <ul className={styles.favorites}>
      {favoritePages.map((pageKey) => {
        const title = getTitleById(pageKey);
        const route = getRouteByKey(pageKey);
        const url = route?.PATH() || '#';
        const { item, section } = getItemAndSectionByPageKey(pageKey);
        const Icon = item?.icon || section?.icon;

        return (
          <li
            key={pageKey}
            className={styles.card}
          >
            <Link
              className={styles.link}
              to={url}
            >
              <div className={cn(styles.icon, { [styles.section_icon]: !item?.icon })}>{Icon && <Icon />}</div>
              <p>{title}</p>
            </Link>

            <FavoriteButton
              className={styles.remove_icon}
              pageId={pageKey}
            />
          </li>
        );
      })}
    </ul>
  );
}
