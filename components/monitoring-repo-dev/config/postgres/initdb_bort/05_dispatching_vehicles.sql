-- ==============================================================================
-- 05_dispatching_vehicles.sql
-- ==============================================================================
--
-- Назначение: Справочник транспортных средств для dispatching БД
--
-- Создаёт:
--   - Таблицу vehicles (справочник флота)
--   - Utility функцию update_updated_at_column()
--   - Триггер для автоматического обновления updated_at
--   - Демо-данные (активный vehicle из VEHICLE_ID env variable)
--
-- Используется:
--   - Trip Service: создание рейсов, валидация vehicle_id, API управления флотом
--   - eKuiper: lookup для динамической конфигурации и обогащения данных
--
-- ==============================================================================

-- Подключение к БД dispatching
\c dispatching;

-- ==============================================================================
-- VEHICLES TABLE - Справочник транспортных средств
-- ==============================================================================

-- Создание таблицы vehicles
CREATE TABLE IF NOT EXISTS public.vehicles (
    id SERIAL PRIMARY KEY,
    truck_id VARCHAR(50) NOT NULL UNIQUE,
    vehicle_type VARCHAR(50) NOT NULL,
    bort_number VARCHAR(50),
    equipment_id VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Индекс для lookup производительности (используется eKuiper и Trip Service)
CREATE INDEX IF NOT EXISTS ix_vehicles_is_active ON public.vehicles (is_active, truck_id);

-- Комментарий к таблице
COMMENT ON TABLE public.vehicles IS 
'Справочник транспортных средств. Используется Trip Service для управления флотом и eKuiper для lookup.';

-- ==============================================================================
-- UTILITY FUNCTION - Автоматическое обновление updated_at
-- ==============================================================================

-- Функция для обновления updated_at (может использоваться другими таблицами)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер для автоматического обновления updated_at
CREATE TRIGGER update_vehicles_updated_at 
BEFORE UPDATE ON public.vehicles
FOR EACH ROW 
EXECUTE FUNCTION update_updated_at_column();

-- ==============================================================================
-- DEMO DATA INITIALIZATION
-- ==============================================================================

-- Инициализация демо-данных
-- Использует переменную окружения VEHICLE_ID для определения активного транспорта
DO $$
DECLARE
    env_vehicle_id VARCHAR(50);
BEGIN
    -- Получаем VEHICLE_ID из переменной окружения (по умолчанию 4)
    env_vehicle_id := COALESCE(
        current_setting('dispatching.vehicle_id', true), 
        '4'
    );
    
    -- Вставляем активный vehicle из переменной окружения
    INSERT INTO public.vehicles (truck_id, vehicle_type, bort_number, is_active, equipment_id) 
    VALUES (env_vehicle_id, 'mining_truck', 'AC9', TRUE, 'eq_' || env_vehicle_id)
    ON CONFLICT (truck_id) 
    DO UPDATE SET 
        is_active = TRUE, 
        updated_at = NOW();
    
    -- Вставляем другие vehicles как неактивные (для примера)
    INSERT INTO public.vehicles (truck_id, vehicle_type, bort_number, is_active) 
    VALUES 
        ('9_truck', 'mining_truck', 'AC9_old', FALSE),
        ('5_truck', 'mining_truck', 'AC5', FALSE)
    ON CONFLICT (truck_id) DO NOTHING;
    
    RAISE NOTICE 'Configured active vehicle: %', env_vehicle_id;
EXCEPTION
    WHEN OTHERS THEN
        -- Игнорируем ошибки инициализации (если нет прав на current_setting)
        RAISE NOTICE 'Failed to initialize vehicles: %', SQLERRM;
END $$;

-- Права для postgres пользователя
GRANT ALL PRIVILEGES ON TABLE public.vehicles TO postgres;
GRANT ALL PRIVILEGES ON SEQUENCE public.vehicles_id_seq TO postgres;

