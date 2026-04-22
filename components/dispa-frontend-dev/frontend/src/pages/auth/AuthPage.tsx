import React, { useState } from 'react';
import { authServiceApi } from '@/shared/api/authServiceApi';

export const AuthPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [testingConnection, setTestingConnection] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await authServiceApi.login({ username, password });
      setResult(data);
    } catch (err: any) {
      console.error('Auth error:', err);
      if (err.code === 'ECONNREFUSED' || err.message?.includes('Network Error')) {
        setError('Сервер авторизации недоступен. Проверьте, что auth-сервис запущен на порту 8001');
      } else if (err.response?.status === 500) {
        setError('Ошибка сервера (500). Проверьте, что auth-сервис работает корректно');
      } else if (err.response?.status === 404) {
        setError('Эндпоинт /auth/login не найден. Проверьте конфигурацию auth-сервиса');
      } else if (err.response?.status === 401) {
        setError('Неверные учетные данные');
      } else {
        setError(`Ошибка авторизации: ${err.message || 'Неизвестная ошибка'}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async () => {
    setTestingConnection(true);
    setError(null);
    try {
      // Пробуем простой GET запрос для проверки доступности сервера
      const response = await fetch('/auth-api/health', { method: 'GET' });
      if (response.ok) {
        setError('✅ Сервер auth-сервиса доступен');
      } else {
        setError(`⚠️ Сервер отвечает, но с ошибкой: ${response.status}`);
      }
    } catch (err: any) {
      console.error('Connection test error:', err);
      setError('❌ Сервер auth-сервиса недоступен. Проверьте, что он запущен на порту 8001');
    } finally {
      setTestingConnection(false);
    }
  };

  return (
    <div style={{ maxWidth: 360, margin: '64px auto' }}>
      <h2>Вход</h2>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <label>
          Логин
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="username"
            required
            style={{ width: '100%', padding: 8 }}
          />
        </label>
        <label>
          Пароль
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="password"
            required
            style={{ width: '100%', padding: 8 }}
          />
        </label>
        <button type="submit" disabled={loading} style={{ padding: '10px 12px' }}>
          {loading ? 'Входим…' : 'Войти'}
        </button>
      </form>

      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <button 
          onClick={testConnection} 
          disabled={testingConnection}
          style={{ padding: '8px 12px', fontSize: '14px' }}
        >
          {testingConnection ? 'Проверяем...' : 'Проверить подключение'}
        </button>
      </div>

      {error && (
        <div style={{ marginTop: 12, color: 'red' }}>{error}</div>
      )}
      {result && (
        <pre style={{ marginTop: 12, background: '#f7f7f7', padding: 12, overflow: 'auto' }}>
{JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
};


