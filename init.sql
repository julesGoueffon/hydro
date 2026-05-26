-- Ce script sera exécuté automatiquement par l'image Docker Postgres au premier lancement
-- (à condition que le dossier postgres_data soit vide).

-- ==========================================
-- 1. TABLES TEMPORELLES (HYPERTABLES)
-- ==========================================

-- A. Table Télémétrie standard (Format étroit, idéal pour tes ESP)
CREATE TABLE IF NOT EXISTS telemetry (
    "time" TIMESTAMP WITH TIME ZONE NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    metric VARCHAR(50) NOT NULL,
    value DOUBLE PRECISION NOT NULL
);
-- Transformation magique en Hypertable TimescaleDB partitionnée par 7 jours par défaut
SELECT create_hypertable('telemetry', 'time', if_not_exists => TRUE);


-- B. Table Météo (Spécifique pour correspondre EXACTEMENT à ton weather_processor.py)
CREATE TABLE IF NOT EXISTS weather_metrics (
    "time" TIMESTAMP WITH TIME ZONE NOT NULL,
    sensor_name VARCHAR(50),
    temperature DOUBLE PRECISION,
    windspeed DOUBLE PRECISION,
    weathercode INTEGER
);
SELECT create_hypertable('weather_metrics', 'time', if_not_exists => TRUE);


-- C. Table Logs Actionneurs (Pour tracer les pulses des pompes - Modifiée pour Event Sourcing)
CREATE TABLE IF NOT EXISTS actuator_logs (
    id SERIAL,
    "time" TIMESTAMP WITH TIME ZONE NOT NULL,
    actuator_id VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    status VARCHAR(20), -- AJOUTÉ : Pour stocker STARTED, COMPLETED, etc.
    duration_ms INTEGER,
    trigger_source VARCHAR(50)
);
SELECT create_hypertable('actuator_logs', 'time', if_not_exists => TRUE);


-- ==========================================
-- 2. TABLES CLASSIQUES (RELATIONNEL)
-- ==========================================

-- D. Table des images (Pour correspondre EXACTEMENT à ton image_processor.py)
CREATE TABLE IF NOT EXISTS image_metrics (
    sensor_name VARCHAR(50),
    "timestamp" BIGINT NOT NULL,
    image_path VARCHAR(255),
    blur_score DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS video_metrics (
    sensor_name VARCHAR(50),
    "timestamp" BIGINT NOT NULL,
    video_path VARCHAR(255),
    video_type VARCHAR(50)
);

-- E. Événements système (Alertes, pannes, etc.)
CREATE TABLE IF NOT EXISTS system_events (
    id SERIAL PRIMARY KEY,
    "time" TIMESTAMP WITH TIME ZONE NOT NULL,
    level VARCHAR(20),
    category VARCHAR(50),
    message TEXT,
    is_resolved BOOLEAN DEFAULT FALSE
);


-- G. Configuration système (Les cibles de la serre - Corrigée pour les 3 modes)
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    target_ph DOUBLE PRECISION NOT NULL DEFAULT 6.0,
    target_ec DOUBLE PRECISION NOT NULL DEFAULT 1.4,
    system_mode VARCHAR(20) NOT NULL DEFAULT 'AUTO', -- CORRIGÉ : Remplace mode_auto
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insertion des valeurs par défaut pour que l'ID 1 existe toujours
-- (Indispensable pour que Celery ne crashe pas au démarrage)
INSERT INTO system_config (id, target_ph, target_ec, system_mode)
VALUES (1, 6.0, 1.4, 'AUTO')
ON CONFLICT (id) DO NOTHING;

-- TODO check si les 2 table sont bien utiles
CREATE TABLE IF NOT EXISTS calibration_history (
    id SERIAL PRIMARY KEY,
    "timestamp" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    sensor_id VARCHAR(50) NOT NULL,
    old_intercept DOUBLE PRECISION,
    new_intercept DOUBLE PRECISION,
    buffer_value DOUBLE PRECISION
);

-- F. Calibration des sondes analogiques
CREATE TABLE IF NOT EXISTS sensor_calibrations (
    id SERIAL PRIMARY KEY,
    sensor_id VARCHAR(50) UNIQUE NOT NULL,
    slope DOUBLE PRECISION NOT NULL,
    intercept DOUBLE PRECISION NOT NULL,
    last_calibrated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS device_settings (
    device_id VARCHAR(50) PRIMARY KEY,
    telemetry_interval_sec INTEGER NOT NULL DEFAULT 600, -- Fréquence d'envoi global au serveur (ex: 600s = 10 min)
    ph_read_interval_ms INTEGER NOT NULL DEFAULT 2000,   -- Fréquence de lecture matérielle pH
    ec_read_interval_ms INTEGER NOT NULL DEFAULT 2000,   -- Fréquence de lecture matérielle EC
    temp_read_interval_ms INTEGER NOT NULL DEFAULT 5000, -- Fréquence de lecture Température
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- On insère ton ESP32 actuel par défaut pour que l'API ait quelque chose à lire
INSERT INTO device_settings (device_id, telemetry_interval_sec, ph_read_interval_ms, ec_read_interval_ms, temp_read_interval_ms)
VALUES ('mock_node2_wet', 600, 2000, 2000, 5000)
ON CONFLICT (device_id) DO NOTHING;