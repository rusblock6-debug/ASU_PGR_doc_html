import StarFillIcon from '@/shared/assets/icons/ic-star-fill.svg?react';
import StarIcon from '@/shared/assets/icons/ic-star.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import type { AppRouteType } from '@/shared/routes/router';
import { AppButton } from '@/shared/ui/AppButton';

import { useFavoritePages } from '../../model/FavoritePagesContext';

import styles from './FavoriteButton.module.css';

interface FavoriteButtonProps {
  readonly pageId: AppRouteType;
  readonly tabIndex?: number;
  readonly className?: string;
}

export function FavoriteButton({ pageId, tabIndex, className }: FavoriteButtonProps) {
  const { addToFavorites, removeFromFavorites, isFavorite } = useFavoritePages();

  const isInFavorites = isFavorite(pageId);

  const handleClick = () => {
    if (isInFavorites) {
      removeFromFavorites(pageId);
    } else {
      addToFavorites(pageId);
    }
  };

  return (
    <AppButton
      className={cn(styles.button, className)}
      variant="clear"
      size="xs"
      onClick={handleClick}
      title={isInFavorites ? 'Удалить из избранного' : 'Добавить в избранное'}
      tabIndex={tabIndex}
      data-visible={isInFavorites}
      onlyIcon
    >
      {isInFavorites ? <StarFillIcon /> : <StarIcon />}
    </AppButton>
  );
}
