-- SQLite reference DDL for the independent PocketTally authentication database.
-- This file is intentionally separate from backend/db/schema.sql: the ledger
-- backup/export workflow never copies credentials or session state.

PRAGMA foreign_keys = ON;

CREATE TABLE owner (
    id INTEGER PRIMARY KEY NOT NULL,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    password_changed_at DATETIME NOT NULL
);

CREATE TABLE sessions (
    id TEXT PRIMARY KEY NOT NULL,
    token_digest TEXT NOT NULL UNIQUE,
    created_at DATETIME NOT NULL,
    last_seen_at DATETIME NOT NULL,
    absolute_expires_at DATETIME NOT NULL,
    client_ip TEXT NOT NULL,
    user_agent TEXT NOT NULL
);

CREATE TABLE login_throttle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_ip TEXT NOT NULL UNIQUE,
    failures INTEGER NOT NULL DEFAULT 0,
    window_started_at DATETIME NOT NULL,
    blocked_until DATETIME,
    updated_at DATETIME NOT NULL
);

PRAGMA user_version = 1;
