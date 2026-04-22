/**
 * Компонент заголовка приложения с навигацией
 */
import React from 'react';

type ViewType = 'settings' | 'graphs' | 'editor' | 'viewer';

interface AppHeaderProps {
  currentView: ViewType;
  onViewChange: (view: ViewType) => void;
  onShowHorizonsModal?: () => void;
}

export function AppHeader({ currentView, onViewChange, onShowHorizonsModal }: AppHeaderProps) {
  return (
    <header className="app-header">
      <h1 style={{ color: '#fe6f31', fontWeight: 700 }}>Graph Service - Редактор дорог шахты</h1>
      <nav className="app-nav">
        <button 
          className={`nav-button ${currentView === 'settings' ? 'active' : ''}`}
          onClick={() => onViewChange('settings')}
        >
          ⚙️ Настройки
        </button>
        <button 
          className={`nav-button ${currentView === 'graphs' ? 'active' : ''}`}
          onClick={() => {
            if (onShowHorizonsModal) {
              onShowHorizonsModal();
            }
          }}
          title="Просмотреть горизонты"
        >
          Графы
        </button>
        <button 
          className={`nav-button ${currentView === 'editor' ? 'active' : ''}`}
          onClick={() => onViewChange('editor')}
        >
          Редактирование
        </button>
        <button 
          className="nav-button"
          onClick={() => onViewChange('viewer')}
        >
          Просмотр
        </button>
      </nav>
    </header>
  );
}



