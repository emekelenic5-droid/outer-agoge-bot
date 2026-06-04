"""
database.py — All data operations for OUTER AGOGE Bot v2
"""

import sqlite3
import os
from datetime import date, timedelta
from typing import Optional, List

DB_PATH = os.getenv("DB_PATH", "outer_agoge.db")

MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

VALID_CHANNEL_TYPES = ["gm", "accountability", "business", "fitness", "lifestyle"]


# ─── CONNECTION ────────────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ─── INIT ──────────────────────────────────────────────────────────────────────

def init_db() -> None:
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS members (
            telegram_id  INTEGER PRIMARY KEY,
            username     TEXT    DEFAULT '',
            name         TEXT    DEFAULT '',
            joined_date  TEXT    DEFAULT (date('now'))
        );

        -- Maps topic thread_id → channel type (gm, accountability, business, fitness)
        CREATE TABLE IF NOT EXISTS channel_config (
            chat_id      INTEGER NOT NULL,
            thread_id    INTEGER,
            channel_type TEXT    NOT NULL,
            PRIMARY KEY (chat_id, channel_type)
        );

        CREATE TABLE IF NOT EXISTS gm_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id  INTEGER NOT NULL,
            date         TEXT    NOT NULL,
            UNIQUE(telegram_id, date)
        );

        CREATE TABLE IF NOT EXISTS report_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id  INTEGER NOT NULL,
            date         TEXT    NOT NULL,
            text         TEXT,
            UNIQUE(telegram_id, date)
        );

        CREATE TABLE IF NOT EXISTS money_in (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id  INTEGER NOT NULL,
            amount       REAL    NOT NULL DEFAULT 0,
            month        INTEGER NOT NULL,
            year         INTEGER NOT NULL,
            submitted_at TEXT    DEFAULT (datetime('now')),
            UNIQUE(telegram_id, month, year)
        );

        CREATE TABLE IF NOT EXISTS fitness_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id  INTEGER NOT NULL,
            date         TEXT    NOT NULL,
            text         TEXT
        );

        CREATE TABLE IF NOT EXISTS badges (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id  INTEGER NOT NULL,
            badge_type   TEXT    NOT NULL,
            month        INTEGER NOT NULL,
            year         INTEGER NOT NULL,
            awarded_at   TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS challenges (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            description  TEXT    NOT NULL,
            posted_by    INTEGER,
            posted_at    TEXT    DEFAULT (datetime('now')),
            winner_id    INTEGER,
            completed_at TEXT,
            active       INTEGER DEFAULT 1
        );
    """)
    conn.commit()
    conn.close()


# ─── CHANNEL CONFIG ────────────────────────────────────────────────────────────

def register_channel(chat_id: int, thread_id: Optional[int], channel_type: str) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO channel_config (chat_id, thread_id, channel_type)
           VALUES (?, ?, ?)
           ON CONFLICT(chat_id, channel_type)
           DO UPDATE SET thread_id=excluded.thread_id""",
        (chat_id, thread_id, channel_type)
    )
    conn.commit()
    conn.close()


def get_channel_type(chat_id: int, thread_id: Optional[int]) -> Optional[str]:
    """Returns the channel type for this thread, or None if not configured."""
    conn = get_conn()
    row = conn.execute(
        """SELECT channel_type FROM channel_config
           WHERE chat_id=? AND (thread_id=? OR (thread_id IS NULL AND ? IS NULL))""",
        (chat_id, thread_id, thread_id)
    ).fetchone()
    conn.close()
    return row["channel_type"] if row else None


def get_all_channel_config(chat_id: int) -> List[sqlite3.Row]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM channel_config WHERE chat_id=? ORDER BY channel_type",
        (chat_id,)
    ).fetchall()
    conn.close()
    return rows


# ─── MEMBERS ───────────────────────────────────────────────────────────────────

def register_member(telegram_id: int, username: str, name: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO members (telegram_id, username, name) VALUES (?, ?, ?)",
        (telegram_id, username or "", name or "")
    )
    conn.execute(
        "UPDATE members SET username=?, name=? WHERE telegram_id=?",
        (username or "", name or "", telegram_id)
    )
    conn.commit()
    conn.close()


def get_member(telegram_id: int) -> Optional[sqlite3.Row]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM members WHERE telegram_id=?", (telegram_id,)).fetchone()
    conn.close()
    return row


def get_member_by_username(username: str) -> Optional[sqlite3.Row]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM members WHERE LOWER(username)=LOWER(?)",
        (username.lstrip("@"),)
    ).fetchone()
    conn.close()
    return row


def get_all_members() -> List[sqlite3.Row]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM members ORDER BY name").fetchall()
    conn.close()
    return rows


def display_name(member: sqlite3.Row) -> str:
    return member["name"] or member["username"] or "Spartan"


# ─── GM LOG ────────────────────────────────────────────────────────────────────

def log_gm(telegram_id: int) -> bool:
    """True = newly logged, False = already logged today."""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO gm_log (telegram_id, date) VALUES (?, ?)",
            (telegram_id, date.today().isoformat())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_gm_streak(telegram_id: int) -> int:
    conn = get_conn()
    streak, check = 0, date.today()
    while True:
        row = conn.execute(
            "SELECT 1 FROM gm_log WHERE telegram_id=? AND date=?",
            (telegram_id, check.isoformat())
        ).fetchone()
        if row:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    conn.close()
    return streak


def get_gm_count_month(telegram_id: int, month: int, year: int) -> int:
    conn = get_conn()
    row = conn.execute(
        """SELECT COUNT(*) AS cnt FROM gm_log
           WHERE telegram_id=?
             AND strftime('%m', date)=? AND strftime('%Y', date)=?""",
        (telegram_id, f"{month:02d}", str(year))
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


# ─── REPORT LOG ────────────────────────────────────────────────────────────────

def log_report(telegram_id: int, text: str) -> bool:
    """True = new, False = updated."""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO report_log (telegram_id, date, text) VALUES (?, ?, ?)",
            (telegram_id, date.today().isoformat(), text)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        conn.execute(
            "UPDATE report_log SET text=? WHERE telegram_id=? AND date=?",
            (text, telegram_id, date.today().isoformat())
        )
        conn.commit()
        return False
    finally:
        conn.close()


def get_report_streak(telegram_id: int) -> int:
    conn = get_conn()
    streak, check = 0, date.today()
    while True:
        row = conn.execute(
            "SELECT 1 FROM report_log WHERE telegram_id=? AND date=?",
            (telegram_id, check.isoformat())
        ).fetchone()
        if row:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    conn.close()
    return streak


def get_report_count_month(telegram_id: int, month: int, year: int) -> int:
    conn = get_conn()
    row = conn.execute(
        """SELECT COUNT(*) AS cnt FROM report_log
           WHERE telegram_id=?
             AND strftime('%m', date)=? AND strftime('%Y', date)=?""",
        (telegram_id, f"{month:02d}", str(year))
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


# ─── FITNESS LOG ───────────────────────────────────────────────────────────────

def log_fitness(telegram_id: int, text: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO fitness_log (telegram_id, date, text) VALUES (?, ?, ?)",
        (telegram_id, date.today().isoformat(), text)
    )
    conn.commit()
    conn.close()


def get_fitness_count_month(telegram_id: int, month: int, year: int) -> int:
    conn = get_conn()
    row = conn.execute(
        """SELECT COUNT(*) AS cnt FROM fitness_log
           WHERE telegram_id=?
             AND strftime('%m', date)=? AND strftime('%Y', date)=?""",
        (telegram_id, f"{month:02d}", str(year))
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


# ─── MONEY IN ──────────────────────────────────────────────────────────────────

def submit_money_in(telegram_id: int, amount: float, month: int, year: int) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO money_in (telegram_id, amount, month, year)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(telegram_id, month, year)
           DO UPDATE SET amount=excluded.amount, submitted_at=datetime('now')""",
        (telegram_id, amount, month, year)
    )
    conn.commit()
    conn.close()


def get_money_in(telegram_id: int, month: int, year: int) -> float:
    conn = get_conn()
    row = conn.execute(
        "SELECT amount FROM money_in WHERE telegram_id=? AND month=? AND year=?",
        (telegram_id, month, year)
    ).fetchone()
    conn.close()
    return row["amount"] if row else 0.0


def get_leaderboard(month: int, year: int) -> List[sqlite3.Row]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT m.name, m.username, m.telegram_id,
                  COALESCE(mi.amount, 0) AS amount
           FROM members m
           LEFT JOIN money_in mi
             ON mi.telegram_id = m.telegram_id
            AND mi.month=? AND mi.year=?
           ORDER BY amount DESC, m.name""",
        (month, year)
    ).fetchall()
    conn.close()
    return rows


def remove_money_in(telegram_id: int, month: int, year: int) -> bool:
    conn = get_conn()
    c = conn.execute(
        "DELETE FROM money_in WHERE telegram_id=? AND month=? AND year=?",
        (telegram_id, month, year)
    )
    conn.commit()
    deleted = c.rowcount > 0
    conn.close()
    return deleted


# ─── BADGES ────────────────────────────────────────────────────────────────────

def award_badge(telegram_id: int, badge_type: str, month: int, year: int) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO badges (telegram_id, badge_type, month, year) VALUES (?, ?, ?, ?)",
        (telegram_id, badge_type.upper(), month, year)
    )
    conn.commit()
    conn.close()


def get_member_badges(telegram_id: int) -> List[sqlite3.Row]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM badges WHERE telegram_id=? ORDER BY year DESC, month DESC",
        (telegram_id,)
    ).fetchall()
    conn.close()
    return rows


def get_hall_of_record() -> List[sqlite3.Row]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT b.badge_type, b.month, b.year, b.awarded_at,
                  m.name, m.username
           FROM badges b
           JOIN members m ON m.telegram_id = b.telegram_id
           ORDER BY b.year DESC, b.month DESC""",
    ).fetchall()
    conn.close()
    return rows


# ─── CHALLENGES ────────────────────────────────────────────────────────────────

def post_challenge(description: str, posted_by: int) -> None:
    conn = get_conn()
    conn.execute("UPDATE challenges SET active=0 WHERE active=1")
    conn.execute(
        "INSERT INTO challenges (description, posted_by) VALUES (?, ?)",
        (description, posted_by)
    )
    conn.commit()
    conn.close()


def get_active_challenge() -> Optional[sqlite3.Row]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM challenges WHERE active=1").fetchone()
    conn.close()
    return row


def complete_challenge(winner_id: int) -> Optional[sqlite3.Row]:
    conn = get_conn()
    challenge = conn.execute("SELECT * FROM challenges WHERE active=1").fetchone()
    if challenge:
        conn.execute(
            "UPDATE challenges SET winner_id=?, completed_at=datetime('now'), active=0 WHERE id=?",
            (winner_id, challenge["id"])
        )
        conn.commit()
    conn.close()
    return challenge
