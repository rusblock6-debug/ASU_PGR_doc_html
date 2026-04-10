/**
 * Общий layout приложения с боковым меню
 */
import { useEffect, useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import truckIcon from '@/assets/truck-icon-2.png';
import './AppLayout.css';

// Получить номер ШАС из VEHICLE_ID (например, '4_truck' -> '4')
const getShasNumber = (): string => {
  const vehicleId = import.meta.env.VITE_VEHICLE_ID || '';
  const match = vehicleId.match(/(\d+)/);
  if (match && match[1]) {
    return match[1];
  }
  
  // По умолчанию возвращаем '3'
  return '3';
};

export const AppLayout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [currentTime, setCurrentTime] = useState(() => new Date());
  const shasNumber = getShasNumber();

  const isActive = (path: string) => location.pathname === path;
  const showHeader = location.pathname !== '/main';

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Обновляем title страницы с номером ШАС
  useEffect(() => {
    document.title = `ШАС №${shasNumber} - Диспетчеризация`;
  }, [shasNumber]);

  return (
    <div className="app-layout">
      {/* Левое боковое меню */}
      <div className="sidebar">
        <div className="logo">
          <img src={truckIcon} alt="Truck" className="logo-icon" />
          <span className="logo-text">ШАС №{shasNumber}</span>
        </div>
        <nav className="nav-menu">
          <button
            className={`nav-button ${isActive('/main') ? 'active' : ''}`}
            onClick={() => navigate('/main')}
          >
            <span className="nav-icon">🏠</span>
            <span className="nav-label">Главная</span>
          </button>
          <button
            className={`nav-button ${isActive('/shift-tasks') ? 'active' : ''}`}
            onClick={() => navigate('/shift-tasks')}
          >
            <span className="nav-icon">📋</span>
            <span className="nav-label">Список заданий</span>
          </button>
          <button
            className={`nav-button ${isActive('/event-log') ? 'active' : ''}`}
            onClick={() => navigate('/event-log')}
          >
            <span className="nav-icon">📖</span>
            <span className="nav-label">Журнал событий</span>
          </button>
          <button
            className={`nav-button ${isActive('/trip-analytics') ? 'active' : ''}`}
            onClick={() => navigate('/trip-analytics')}
          >
            <span className="nav-icon">📊</span>
            <span className="nav-label">Статистика рейсов</span>
          </button>
          <button
            className={`nav-button ${isActive('/manual-actions') ? 'active' : ''}`}
            onClick={() => navigate('/manual-actions')}
          >
            <span className="nav-icon">🖐️</span>
            <span className="nav-label">Ручные действия</span>
          </button>
          <button
            className={`nav-button ${isActive('/settings') ? 'active' : ''}`}
            onClick={() => navigate('/settings')}
          >
            <span className="nav-icon">⚙️</span>
            <span className="nav-label">Настройки</span>
          </button>
        </nav>
      </div>

      {/* Основной контент */}
      <div className="main-content">
        {/* Хедер */}
        {showHeader && (
          <header className="header">
            <div className="header-info">
              <span>Зарегистрированы на смене: admin</span>
              <span>{currentTime.toLocaleString('ru-RU')}</span>
            </div>
          </header>
        )}

        {/* Содержимое страницы */}
        <div className="page-content">
          <Outlet />
        </div>
      </div>
    </div>
  );
};
