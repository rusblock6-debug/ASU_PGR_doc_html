import classNames from 'classnames';
import classNamesBind from 'classnames/bind';

export const cn = classNames;

// https://gist.github.com/heygrady/316bd69633ce816aee1ca24ab63535db
/** Создает bind-версию classNames для CSS Modules. */
export function createBoundClassNames(styles: Record<string, string>) {
  return classNamesBind.bind(styles);
}
