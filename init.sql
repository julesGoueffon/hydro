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
    "time" TIMESTAMP WITH TIME ZONE NOT NULL, -- Doit correspondre à la String parsable de ton JSON
    sensor_name VARCHAR(50),
    temperature DOUBLE PRECISION,
    windspeed DOUBLE PRECISION,
    weathercode INTEGER
);
SELECT create_hypertable('weather_metrics', 'time', if_not_exists => TRUE);


-- C. Table Logs Actionneurs (Pour tracer les pulses des pompes)
CREATE TABLE IF NOT EXISTS actuator_logs (
    -- Pas de PRIMARY KEY stricte sur une hypertable si on n'inclut pas le temps
    id SERIAL,
    "time" TIMESTAMP WITH TIME ZONE NOT NULL,
    actuator_id VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    duration_ms INTEGER,
    trigger_source VARCHAR(50)
);
SELECT create_hypertable('actuator_logs', 'time', if_not_exists => TRUE);


-- ==========================================
-- 2. TABLES CLASSIQUES (RELATIONNEL)
-- ==========================================

-- D. Table des images (Pour correspondre EXACTEMENT à ton image_processor.py)
-- Note: Dans ton Spark, timestamp est un LongType, on utilise donc BIGINT ici.
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

-- F. Calibration des sondes analogiques
CREATE TABLE IF NOT EXISTS sensor_calibrations (
    id SERIAL PRIMARY KEY,
    sensor_id VARCHAR(50) UNIQUE NOT NULL,
    slope DOUBLE PRECISION NOT NULL,
    intercept DOUBLE PRECISION NOT NULL,
    last_calibrated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);  