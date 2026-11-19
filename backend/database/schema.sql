-- Kshetra Phase 1 schema.
-- Moisture averages are calculated in Python. They are not copied into their own table.
-- estimated_liters stays NULL until a later build stores an explicit estimate or a meter reading.

CREATE TABLE IF NOT EXISTS zones (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    crop_label TEXT NOT NULL,
    low_threshold REAL NOT NULL,
    target_moisture REAL NOT NULL,
    max_duration_sec INTEGER NOT NULL,
    cooldown_sec INTEGER NOT NULL,
    mode TEXT NOT NULL DEFAULT 'manual' CHECK (mode IN ('manual', 'automatic')),
    valve_open INTEGER NOT NULL DEFAULT 0 CHECK (valve_open IN (0, 1))
);

CREATE TABLE IF NOT EXISTS sensors (
    id TEXT PRIMARY KEY,
    zone_id TEXT NOT NULL REFERENCES zones(id),
    label TEXT NOT NULL,
    pos_x REAL NOT NULL,
    pos_y REAL NOT NULL,
    calibration_offset REAL NOT NULL DEFAULT 0,
    calibration_scale REAL NOT NULL DEFAULT 1,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1))
);

CREATE TABLE IF NOT EXISTS sensor_readings (
    id INTEGER PRIMARY KEY,
    sensor_id TEXT NOT NULL REFERENCES sensors(id),
    raw_percent REAL,
    moisture_percent REAL,
    quality TEXT NOT NULL CHECK (quality IN ('ok', 'suspect', 'missing', 'invalid')),
    source TEXT NOT NULL CHECK (source IN ('simulated', 'hardware')),
    recorded_at TEXT NOT NULL,
    sim_time TEXT NOT NULL,
    CHECK (
        (quality = 'missing' AND moisture_percent IS NULL AND raw_percent IS NULL)
        OR (quality = 'invalid')
        OR (quality IN ('ok', 'suspect') AND moisture_percent BETWEEN 0 AND 100)
    )
);

CREATE INDEX IF NOT EXISTS idx_readings_sensor ON sensor_readings (sensor_id, id);

CREATE TABLE IF NOT EXISTS irrigation_events (
    id INTEGER PRIMARY KEY,
    zone_id TEXT NOT NULL REFERENCES zones(id),
    mode TEXT NOT NULL CHECK (mode IN ('manual', 'automatic')),
    reason TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    stop_reason TEXT,
    duration_sec REAL,
    estimated_liters REAL CHECK (estimated_liters IS NULL OR estimated_liters >= 0),
    source TEXT NOT NULL CHECK (source IN ('simulated', 'hardware'))
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY,
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'danger')),
    code TEXT NOT NULL,
    message TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    acknowledged_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_alerts_open ON alerts (code, acknowledged_at);

CREATE TABLE IF NOT EXISTS inspections (
    id INTEGER PRIMARY KEY,
    rover_id TEXT NOT NULL,
    checkpoint_id TEXT,
    image_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('simulated', 'hardware'))
);

CREATE TABLE IF NOT EXISTS plant_reports (
    id INTEGER PRIMARY KEY,
    inspection_id INTEGER NOT NULL REFERENCES inspections(id),
    entry_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('healthy', 'deficiency', 'disease', 'discrepancy', 'uncertain')),
    title TEXT NOT NULL,
    farmer_message TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    treatment_id TEXT,
    dose_seconds INTEGER,
    match_score REAL,
    method TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS treatment_events (
    id INTEGER PRIMARY KEY,
    treatment_id TEXT NOT NULL,
    report_id INTEGER,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    stop_reason TEXT,
    duration_sec REAL,
    max_seconds INTEGER NOT NULL,
    farmer_confirmed INTEGER NOT NULL CHECK (farmer_confirmed IN (0, 1)),
    source TEXT NOT NULL CHECK (source IN ('simulated', 'hardware'))
);
