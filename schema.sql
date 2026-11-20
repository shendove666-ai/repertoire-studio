-- Destructive setup for a newly created database.
DROP TABLE IF EXISTS practice_logs;
DROP TABLE IF EXISTS pieces;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pieces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    composer TEXT NOT NULL,
    opus_catalog TEXT NOT NULL,
    musical_key TEXT NOT NULL,
    musical_form TEXT NOT NULL,
    technical_focus TEXT NOT NULL,
    difficulty INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
    mastery_status TEXT NOT NULL DEFAULT 'In Progress',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE practice_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    piece_id INTEGER NOT NULL,
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    target_bpm INTEGER NOT NULL CHECK (target_bpm > 0),
    measure_range TEXT NOT NULL,
    session_notes TEXT,
    practiced_on DATE NOT NULL DEFAULT (DATE('now')),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (piece_id) REFERENCES pieces (id) ON DELETE CASCADE
);
