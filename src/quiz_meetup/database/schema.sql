CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 1,
    timer_seconds INTEGER NOT NULL DEFAULT 60,
    notes TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rounds_game_id ON rounds(game_id);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    prompt TEXT NOT NULL,
    question_type TEXT NOT NULL DEFAULT 'open',
    notes TEXT NOT NULL DEFAULT '',
    answer TEXT NOT NULL DEFAULT '',
    option_a TEXT NOT NULL DEFAULT '',
    option_b TEXT NOT NULL DEFAULT '',
    option_c TEXT NOT NULL DEFAULT '',
    option_d TEXT NOT NULL DEFAULT '',
    points INTEGER NOT NULL DEFAULT 1,
    order_index INTEGER NOT NULL DEFAULT 1,
    timer_seconds INTEGER NOT NULL DEFAULT 45,
    FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_questions_round_id ON questions(round_id);

CREATE TABLE IF NOT EXISTS media_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER,
    round_id INTEGER,
    question_id INTEGER,
    usage_role TEXT NOT NULL DEFAULT 'library',
    media_type TEXT NOT NULL,
    title TEXT NOT NULL,
    original_filename TEXT NOT NULL DEFAULT '',
    file_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE SET NULL,
    FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE SET NULL,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_media_game_id ON media_assets(game_id);

CREATE TABLE IF NOT EXISTS game_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    session_number INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    completed_round_ids TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    finished_at TEXT,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_game_sessions_game_id ON game_sessions(game_id);
CREATE INDEX IF NOT EXISTS idx_game_sessions_status ON game_sessions(status);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    session_id INTEGER,
    name TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#1F7A8C',
    score INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES game_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_teams_game_id ON teams(game_id);

CREATE TABLE IF NOT EXISTS score_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    round_id INTEGER,
    question_id INTEGER,
    entry_type TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    points INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_score_entries_team_id ON score_entries(team_id);
CREATE INDEX IF NOT EXISTS idx_score_entries_round_id ON score_entries(round_id);
CREATE INDEX IF NOT EXISTS idx_score_entries_question_id ON score_entries(question_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_score_entries_question_unique
ON score_entries(team_id, question_id)
WHERE entry_type = 'question' AND question_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_score_entries_round_adjustment_unique
ON score_entries(team_id, round_id, entry_type)
WHERE entry_type = 'round_adjustment' AND round_id IS NOT NULL AND question_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_score_entries_total_adjustment_unique
ON score_entries(team_id, entry_type)
WHERE entry_type = 'total_adjustment' AND round_id IS NULL AND question_id IS NULL;

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
