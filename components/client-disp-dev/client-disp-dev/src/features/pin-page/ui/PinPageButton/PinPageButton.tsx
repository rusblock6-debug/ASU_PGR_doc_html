import PinFillIcon from '@/shared/assets/icons/ic-pin-fill.svg?react';
import PinIcon from '@/shared/assets/icons/ic-pin.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import type { AppRouteType } from '@/shared/routes/router';
import { AppButton } from '@/shared/ui/AppButton';

import { usePinnedPages } from '../../model/PinnedPagesContext';

import styles from './PinPageButton.module.css';

interface PinPageButtonProps {
  readonly pageId: AppRouteType;
  readonly tabIndex?: number;
  readonly className?: string;
}

export function PinPageButton({ pageId, tabIndex, className }: PinPageButtonProps) {
  const { pinPage, unpinPage, isPinned } = usePinnedPages();

  const pinned = isPinned(pageId);

  const handleClick = () => {
    if (pinned) {
      unpinPage(pageId);
    } else {
      pinPage(pageId);
    }
  };

  return (
    <AppButton
      className={cn(styles.button, className)}
      variant="clear"
      size="xs"
      onClick={handleClick}
      title={pinned ? 'Открепить страницу' : 'Закрепить страницу'}
      tabIndex={tabIndex}
      data-visible={pinned}
      onlyIcon
    >
      {pinned ? <PinFillIcon /> : <PinIcon />}
    </AppButton>
  );
}
