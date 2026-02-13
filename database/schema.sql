-- ============================================================================
-- ESP32 Reminder Management System - Database Schema
-- Version: 1.0
-- Date: 2026-01-08
-- ============================================================================

-- PRAGMA settings for optimization
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA cache_size = -64000;  -- 64MB cache

-- ============================================================================
-- Table: devices
-- Purpose: Store registered ESP32 device information
-- ============================================================================
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mac_address VARCHAR(17) UNIQUE NOT NULL,  -- Format: "aa:bb:cc:dd:ee:ff"
    device_name VARCHAR(100),
    firmware_version VARCHAR(50),
    last_online_at TIMESTAMP,
    last_sync_at TIMESTAMP,
    is_online BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for devices
CREATE INDEX IF NOT EXISTS idx_devices_mac ON devices(mac_address);
CREATE INDEX IF NOT EXISTS idx_devices_online ON devices(is_online);

-- ============================================================================
-- Table: reminders
-- Purpose: Store reminder data for all devices
-- ============================================================================
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    remote_id VARCHAR(100),  -- ESP32-side reminder ID for sync

    -- Reminder content
    content TEXT NOT NULL,

    -- Scheduling fields (MVP: basic support)
    reminder_type VARCHAR(20) NOT NULL DEFAULT 'once',  -- 'once', 'daily'
    scheduled_timestamp INTEGER,  -- Unix timestamp for one-time reminders
    scheduled_time VARCHAR(10),   -- HH:MM format for recurring reminders

    -- Status tracking
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'completed', 'cancelled'
    completed_at TIMESTAMP,

    -- Holiday awareness (for phase 2)
    skip_holidays BOOLEAN DEFAULT FALSE,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50) DEFAULT 'web',  -- 'web', 'device', 'api'
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,

    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Indexes for reminders
CREATE INDEX IF NOT EXISTS idx_reminders_device ON reminders(device_id);
CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status);
CREATE INDEX IF NOT EXISTS idx_reminders_remote_id ON reminders(remote_id);

-- ============================================================================
-- Table: holidays (for phase 2 - Chinese holidays)
-- Purpose: Store Chinese holiday data for smart scheduling
-- ============================================================================
CREATE TABLE IF NOT EXISTS holidays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    holiday_date DATE NOT NULL UNIQUE,
    holiday_name VARCHAR(50) NOT NULL,
    is_observed BOOLEAN DEFAULT TRUE,  -- True if it's a working holiday
    holiday_type VARCHAR(20)  -- 'national', 'traditional', 'adjustment'
);

-- Index for holidays
CREATE INDEX IF NOT EXISTS idx_holidays_date ON holidays(holiday_date);

-- ============================================================================
-- Table: sync_logs
-- Purpose: Track device synchronization history
-- ============================================================================
CREATE TABLE IF NOT EXISTS sync_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    sync_direction VARCHAR(10) NOT NULL,  -- 'push', 'pull', 'bidirectional'
    reminders_sent INTEGER DEFAULT 0,
    reminders_received INTEGER DEFAULT 0,
    reminders_updated INTEGER DEFAULT 0,
    sync_status VARCHAR(20) DEFAULT 'success',  -- 'success', 'partial', 'failed'
    error_message TEXT,
    sync_duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Indexes for sync_logs
CREATE INDEX IF NOT EXISTS idx_sync_logs_device ON sync_logs(device_id);
CREATE INDEX IF NOT EXISTS idx_sync_logs_created ON sync_logs(created_at);

-- ============================================================================
-- Trigger: Auto-update updated_at timestamp
-- ============================================================================
CREATE TRIGGER IF NOT EXISTS update_devices_timestamp
AFTER UPDATE ON devices
BEGIN
    UPDATE devices SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_reminders_timestamp
AFTER UPDATE ON reminders
BEGIN
    UPDATE reminders SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ============================================================================
-- Table: chat_messages
-- Purpose: Store ESP32 dialogue records (STT user input + TTS AI response)
-- ============================================================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,

    -- Dialogue content
    user_text TEXT NOT NULL,        -- User input text (STT recognition result)
    ai_text TEXT NOT NULL,          -- AI response text (TTS synthesis source)

    -- Timestamp (server time override)
    server_timestamp INTEGER NOT NULL,  -- Millisecond timestamp (business key)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Metadata (extension fields)
    session_id VARCHAR(100),        -- Session ID (future support for multi-turn dialogue)
    metadata TEXT,                  -- JSON extension field

    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Key index optimization
CREATE INDEX IF NOT EXISTS idx_chat_device_timestamp
    ON chat_messages(device_id, server_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_chat_timestamp
    ON chat_messages(server_timestamp DESC);

-- ============================================================================
-- Table: ai_reports
-- Purpose: Store daily AI thinking reports (HTML content)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ai_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,

    -- Report identifier
    report_date DATE NOT NULL,      -- Report date (business key)

    -- Report content
    html_content TEXT NOT NULL,     -- Complete HTML report
    chat_count INTEGER DEFAULT 0,   -- Number of associated dialogues

    -- Generation status
    generation_status VARCHAR(20) DEFAULT 'success',  -- success, failed, pending
    error_message TEXT,             -- Error information

    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraint: One report per device per day
    UNIQUE(device_id, report_date),

    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Index optimization
CREATE INDEX IF NOT EXISTS idx_reports_device_date
    ON ai_reports(device_id, report_date DESC);
CREATE INDEX IF NOT EXISTS idx_reports_status
    ON ai_reports(generation_status);

-- ============================================================================
-- Trigger: Auto-update updated_at for ai_reports
-- ============================================================================
CREATE TRIGGER IF NOT EXISTS update_ai_reports_timestamp
AFTER UPDATE ON ai_reports
BEGIN
    UPDATE ai_reports SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
