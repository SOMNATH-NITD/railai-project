-- PostgreSQL + PostGIS Schema for Railway Engine

-- 1. Enable PostGIS for spatial coordinates
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Stations Table
CREATE TABLE IF NOT EXISTS stations (
    station_code VARCHAR(10) PRIMARY KEY,
    station_name VARCHAR(150) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(100),
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(9,6) NOT NULL,
    geom GEOMETRY(Point, 4326),
    is_major_junction BOOLEAN DEFAULT FALSE,
    platform_count INT DEFAULT 2,
    min_transfer_buffer_min INT DEFAULT 30,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stations_geom ON stations USING GIST(geom);

-- 3. Trains Master Table
CREATE TABLE IF NOT EXISTS trains (
    train_number VARCHAR(10) PRIMARY KEY,
    train_name VARCHAR(150) NOT NULL,
    train_type VARCHAR(50) NOT NULL,
    origin_station_code VARCHAR(10) REFERENCES stations(station_code),
    dest_station_code VARCHAR(10) REFERENCES stations(station_code),
    runs_on_mon BOOLEAN DEFAULT TRUE,
    runs_on_tue BOOLEAN DEFAULT TRUE,
    runs_on_wed BOOLEAN DEFAULT TRUE,
    runs_on_thu BOOLEAN DEFAULT TRUE,
    runs_on_fri BOOLEAN DEFAULT TRUE,
    runs_on_sat BOOLEAN DEFAULT TRUE,
    runs_on_sun BOOLEAN DEFAULT TRUE,
    historical_punctuality NUMERIC(5,2) DEFAULT 85.00
);

-- 4. Train Stop Schedules
CREATE TABLE IF NOT EXISTS train_schedules (
    schedule_id BIGSERIAL PRIMARY KEY,
    train_number VARCHAR(10) REFERENCES trains(train_number) ON DELETE CASCADE,
    station_code VARCHAR(10) REFERENCES stations(station_code),
    stop_sequence INT NOT NULL,
    scheduled_arrival TIME NOT NULL,
    scheduled_departure TIME NOT NULL,
    day_offset INT NOT NULL DEFAULT 1,
    distance_km INT NOT NULL DEFAULT 0,
    platform_hint VARCHAR(10),
    UNIQUE(train_number, stop_sequence)
);

CREATE INDEX IF NOT EXISTS idx_schedule_lookup ON train_schedules(station_code, train_number);

-- 5. Real-Time Delay Status Table
CREATE TABLE IF NOT EXISTS live_train_status (
    status_id BIGSERIAL PRIMARY KEY,
    train_number VARCHAR(10) REFERENCES trains(train_number),
    current_station_code VARCHAR(10) REFERENCES stations(station_code),
    delay_minutes INT DEFAULT 0,
    expected_arrival TIMESTAMP WITH TIME ZONE,
    last_gps_sync TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_live_train_delay ON live_train_status(train_number);