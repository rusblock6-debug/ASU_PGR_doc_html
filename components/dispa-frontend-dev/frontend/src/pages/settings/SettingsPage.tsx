import React, { useEffect, useState } from 'react';
import './SettingsPage.css';

interface SettingsData {
  VEHICLE_ID: string;
  EXTERNAL_NANOMQ_HOST: string;
  EXTERNAL_NANOMQ_PORT: string;
  EKUIPER_PORT: string;
  EKUIPER_REST_PORT: string;
  TRIP_SERVICE_PORT: string;
  POSTGRES_PORT: string;
  REDIS_PORT: string;
  NANOMQ_MQTT_PORT: string;
  NANOMQ_WS_PORT: string;
  NANOMQ_ADMIN_PORT: string;
  POSTGRES_DB: string;
  POSTGRES_USER: string;
  REDIS_MAXMEMORY: string;
  REDIS_MAXMEMORY_POLICY: string;
  LOG_LEVEL: string;
}

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);

      // TODO: В будущем это будет API endpoint
      // Пока используем моковые данные из переменных окружения
      const mockSettings: SettingsData = {
        VEHICLE_ID: import.meta.env.VITE_VEHICLE_ID || '4_truck',
        EXTERNAL_NANOMQ_HOST: '10.100.109.25',
        EXTERNAL_NANOMQ_PORT: '1883',
        EKUIPER_PORT: '9081',
        EKUIPER_REST_PORT: '9082',
        TRIP_SERVICE_PORT: '8000',
        POSTGRES_PORT: '5432',
        REDIS_PORT: '6379',
        NANOMQ_MQTT_PORT: '1883',
        NANOMQ_WS_PORT: '8083',
        NANOMQ_ADMIN_PORT: '8081',
        POSTGRES_DB: 'dispatching',
        POSTGRES_USER: 'postgres',
        REDIS_MAXMEMORY: '4gb',
        REDIS_MAXMEMORY_POLICY: 'allkeys-lru',
        LOG_LEVEL: 'INFO',
      };

      setSettings(mockSettings);
    } catch (err) {
      console.error('Error loading settings:', err);
      setError('Не удалось загрузить настройки');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-page">
        <div className="loading">Загрузка настроек...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="settings-page">
        <div className="error-message">{error}</div>
      </div>
    );
  }

  if (!settings) {
    return null;
  }

  const settingsGroups = [
    {
      title: 'Конфигурация транспорта',
      items: [
        { key: 'VEHICLE_ID', label: 'ID машины', value: settings.VEHICLE_ID },
      ],
    },
    {
      title: 'Внешний MQTT брокер',
      items: [
        { key: 'EXTERNAL_NANOMQ_HOST', label: 'Хост', value: settings.EXTERNAL_NANOMQ_HOST },
        { key: 'EXTERNAL_NANOMQ_PORT', label: 'Порт', value: settings.EXTERNAL_NANOMQ_PORT },
      ],
    },
    {
      title: 'Порты сервисов',
      items: [
        { key: 'TRIP_SERVICE_PORT', label: 'Trip Service', value: settings.TRIP_SERVICE_PORT },
        { key: 'EKUIPER_PORT', label: 'eKuiper', value: settings.EKUIPER_PORT },
        { key: 'EKUIPER_REST_PORT', label: 'eKuiper REST API', value: settings.EKUIPER_REST_PORT },
        { key: 'NANOMQ_MQTT_PORT', label: 'NanoMQ MQTT', value: settings.NANOMQ_MQTT_PORT },
        { key: 'NANOMQ_WS_PORT', label: 'NanoMQ WebSocket', value: settings.NANOMQ_WS_PORT },
        { key: 'NANOMQ_ADMIN_PORT', label: 'NanoMQ Admin', value: settings.NANOMQ_ADMIN_PORT },
        { key: 'POSTGRES_PORT', label: 'PostgreSQL', value: settings.POSTGRES_PORT },
        { key: 'REDIS_PORT', label: 'Redis', value: settings.REDIS_PORT },
      ],
    },
    {
      title: 'База данных',
      items: [
        { key: 'POSTGRES_DB', label: 'Имя БД', value: settings.POSTGRES_DB },
        { key: 'POSTGRES_USER', label: 'Пользователь', value: settings.POSTGRES_USER },
      ],
    },
    {
      title: 'Redis',
      items: [
        { key: 'REDIS_MAXMEMORY', label: 'Максимальная память', value: settings.REDIS_MAXMEMORY },
        { key: 'REDIS_MAXMEMORY_POLICY', label: 'Политика вытеснения', value: settings.REDIS_MAXMEMORY_POLICY },
      ],
    },
    {
      title: 'Логирование',
      items: [
        { key: 'LOG_LEVEL', label: 'Уровень логирования', value: settings.LOG_LEVEL },
      ],
    },
  ];

  return (
    <div className="settings-page">
      <div className="settings-header">
        <h1>Настройки</h1>
        <p className="subtitle">Конфигурация системы диспетчеризации</p>
      </div>

      <div className="settings-content">
        {settingsGroups.map((group) => (
          <div key={group.title} className="settings-group">
            <h2 className="group-title">{group.title}</h2>
            <div className="settings-list">
              {group.items.map((item) => (
                <div key={item.key} className="setting-item">
                  <div className="setting-label">{item.label}</div>
                  <div className="setting-value">{item.value}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="settings-footer">
        <div className="info-message">
          <span className="info-icon">ℹ️</span>
          <span>Настройки загружаются из файла <code>.env</code> в корне проекта</span>
        </div>
      </div>
    </div>
  );
};


