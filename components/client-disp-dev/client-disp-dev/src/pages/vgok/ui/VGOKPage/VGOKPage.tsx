import { Link } from 'react-router-dom';

import { getRouteMain } from '@/shared/routes/router';

/**
 * Представляет компонент страницы "Контроль ПНР ВГОК".
 */
export function VGOKPage() {
  return (
    <div>
      <p>Скоро тут будет страница «Контроль ПНР ВГОК»</p>
      <br />
      <Link to={getRouteMain()}>Вернуться на главную</Link>
    </div>
  );
}
