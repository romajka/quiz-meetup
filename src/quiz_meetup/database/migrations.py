from __future__ import annotations

from quiz_meetup.database.connection import Database
from quiz_meetup.resources import read_text_resource


def initialize_database(database: Database) -> None:
    database.executescript(read_text_resource("database", "schema.sql"))
    _migrate_rounds_table(database)
    _migrate_game_sessions_table(database)
    _migrate_questions_table(database)
    _migrate_media_assets_table(database)
    _migrate_teams_table(database)
    _migrate_score_entries_table(database)


def _migrate_rounds_table(database: Database) -> None:
    existing_columns = {
        row["name"] for row in database.fetchall("PRAGMA table_info(rounds)")
    }
    required_columns = {
        "round_type": "TEXT NOT NULL DEFAULT 'standard'",
        "settings_text": "TEXT NOT NULL DEFAULT ''",
    }
    for column_name, definition in required_columns.items():
        if column_name not in existing_columns:
            database.execute(
                f"ALTER TABLE rounds ADD COLUMN {column_name} {definition}"
            )


def _migrate_game_sessions_table(database: Database) -> None:
    database.execute(
        """
        CREATE TABLE IF NOT EXISTS game_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            session_number INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            completed_round_ids TEXT NOT NULL DEFAULT '',
            active_round_id INTEGER,
            active_question_id INTEGER,
            display_phase TEXT NOT NULL DEFAULT 'waiting',
            started_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            finished_at TEXT,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
            FOREIGN KEY (active_round_id) REFERENCES rounds(id) ON DELETE SET NULL,
            FOREIGN KEY (active_question_id) REFERENCES questions(id) ON DELETE SET NULL
        )
        """
    )
    existing_columns = {
        row["name"] for row in database.fetchall("PRAGMA table_info(game_sessions)")
    }
    required_columns = {
        "active_round_id": "INTEGER",
        "active_question_id": "INTEGER",
        "display_phase": "TEXT NOT NULL DEFAULT 'waiting'",
    }
    for column_name, definition in required_columns.items():
        if column_name not in existing_columns:
            database.execute(
                f"ALTER TABLE game_sessions ADD COLUMN {column_name} {definition}"
            )
    database.execute(
        "CREATE INDEX IF NOT EXISTS idx_game_sessions_game_id ON game_sessions(game_id)"
    )
    database.execute(
        "CREATE INDEX IF NOT EXISTS idx_game_sessions_status ON game_sessions(status)"
    )
    database.execute(
        "CREATE INDEX IF NOT EXISTS idx_game_sessions_active_round_id ON game_sessions(active_round_id)"
    )
    database.execute(
        "CREATE INDEX IF NOT EXISTS idx_game_sessions_active_question_id ON game_sessions(active_question_id)"
    )


def _migrate_questions_table(database: Database) -> None:
    existing_columns = {
        row["name"] for row in database.fetchall("PRAGMA table_info(questions)")
    }
    required_columns = {
        "question_type": "TEXT NOT NULL DEFAULT 'open'",
        "notes": "TEXT NOT NULL DEFAULT ''",
        "option_a": "TEXT NOT NULL DEFAULT ''",
        "option_b": "TEXT NOT NULL DEFAULT ''",
        "option_c": "TEXT NOT NULL DEFAULT ''",
        "option_d": "TEXT NOT NULL DEFAULT ''",
    }

    for column_name, definition in required_columns.items():
        if column_name not in existing_columns:
            database.execute(
                f"ALTER TABLE questions ADD COLUMN {column_name} {definition}"
            )


def _migrate_media_assets_table(database: Database) -> None:
    existing_columns = {
        row["name"] for row in database.fetchall("PRAGMA table_info(media_assets)")
    }
    required_columns = {
        "round_id": "INTEGER",
        "usage_role": "TEXT NOT NULL DEFAULT 'library'",
        "original_filename": "TEXT NOT NULL DEFAULT ''",
    }

    for column_name, definition in required_columns.items():
        if column_name not in existing_columns:
            database.execute(
                f"ALTER TABLE media_assets ADD COLUMN {column_name} {definition}"
            )

    database.execute(
        "CREATE INDEX IF NOT EXISTS idx_media_round_id ON media_assets(round_id)"
    )
    database.execute(
        "CREATE INDEX IF NOT EXISTS idx_media_question_id ON media_assets(question_id)"
    )


def _migrate_teams_table(database: Database) -> None:
    existing_columns = {row["name"] for row in database.fetchall("PRAGMA table_info(teams)")}
    if "session_id" not in existing_columns:
        database.execute("ALTER TABLE teams ADD COLUMN session_id INTEGER")

    database.execute(
        "CREATE INDEX IF NOT EXISTS idx_teams_session_id ON teams(session_id)"
    )


def _migrate_score_entries_table(database: Database) -> None:
    database.execute(
        """
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
        )
        """
    )
    database.execute(
        "CREATE INDEX IF NOT EXISTS idx_score_entries_team_id ON score_entries(team_id)"
    )
    database.execute(
        "CREATE INDEX IF NOT EXISTS idx_score_entries_round_id ON score_entries(round_id)"
    )
    database.execute(
        "CREATE INDEX IF NOT EXISTS idx_score_entries_question_id ON score_entries(question_id)"
    )
    database.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_score_entries_question_unique
        ON score_entries(team_id, question_id)
        WHERE entry_type = 'question' AND question_id IS NOT NULL
        """
    )
    database.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_score_entries_round_adjustment_unique
        ON score_entries(team_id, round_id, entry_type)
        WHERE entry_type = 'round_adjustment' AND round_id IS NOT NULL AND question_id IS NULL
        """
    )
    database.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_score_entries_total_adjustment_unique
        ON score_entries(team_id, entry_type)
        WHERE entry_type = 'total_adjustment' AND round_id IS NULL AND question_id IS NULL
        """
    )

    existing_entries_count = database.fetchone(
        "SELECT COUNT(*) AS count FROM score_entries"
    )["count"]
    if existing_entries_count > 0:
        return

    teams_with_scores = database.fetchall(
        "SELECT id, score, created_at FROM teams WHERE score <> 0"
    )
    for team in teams_with_scores:
        timestamp = team["created_at"]
        database.execute(
            """
            INSERT INTO score_entries (
                team_id, round_id, question_id, entry_type, label, points, created_at, updated_at
            )
            VALUES (?, NULL, NULL, 'total_adjustment', 'Перенесённый итоговый счёт', ?, ?, ?)
            """,
            (team["id"], team["score"], timestamp, timestamp),
        )
