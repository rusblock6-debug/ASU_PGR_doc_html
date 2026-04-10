import { Link } from 'react-router-dom';

import { getRouteMain } from '@/shared/routes/router';

export function LearningPage() {
  return (
    <div>
      <p>Скоро тут будет страница «Обучение»</p>
      <br />
      <Link to={getRouteMain()}>Вернуться на главную</Link>
    </div>
  );
}
