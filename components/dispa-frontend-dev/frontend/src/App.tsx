/**
 * Главный компонент приложения с роутингом
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainPage } from './pages/main/MainPage';
import { ShiftTasksPage } from './pages/shift-tasks/ShiftTasksPage';
import { EventLogPage } from './pages/event-log/EventLogPage';
import { TripAnalyticsPage } from './pages/trip-analytics/TripAnalyticsPage';
import { ManualActionsPage } from './pages/manual-actions/ManualActionsPage';
import { SettingsPage } from './pages/settings/SettingsPage';
import { AppLayout } from './layouts/AppLayout';
import { AuthPage } from './pages/auth/AuthPage';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Страницы авторизации без общего лейаута */}
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/login" element={<AuthPage />} />
        <Route path="/auth/login" element={<AuthPage />} />
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Navigate to="/main" replace />} />
          <Route path="main" element={<MainPage />} />
          <Route path="shift-tasks" element={<ShiftTasksPage />} />
          <Route path="event-log" element={<EventLogPage />} />
          <Route path="trip-analytics" element={<TripAnalyticsPage />} />
          <Route path="manual-actions" element={<ManualActionsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

