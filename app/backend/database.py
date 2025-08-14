import os
import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class DatabaseManager:
    """Lightweight wrapper around SQLite for app persistence.

    Tables:
      - chats(id INTEGER PRIMARY KEY, created_at TEXT, session_id TEXT, sender TEXT, message TEXT, meta TEXT)
      - unanswered(id INTEGER PRIMARY KEY, created_at TEXT, question TEXT, status TEXT, answer TEXT)
      - scans(id INTEGER PRIMARY KEY, started_at TEXT, ended_at TEXT, status TEXT, findings TEXT)
      - settings(key TEXT PRIMARY KEY, value TEXT)
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL,
                session_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                meta TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS unanswered (
                id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL,
                question TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                answer TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT NOT NULL,
                findings TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        self._conn.commit()

    # Settings
    def set_setting(self, key: str, value: Any) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value) if not isinstance(value, str) else value),
        )
        self._conn.commit()

    def get_setting(self, key: str, default: Optional[Any] = None) -> Any:
        cur = self._conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        if not row:
            return default
        value = row[0]
        try:
            return json.loads(value)
        except Exception:
            return value

    # Chats
    def add_chat_message(self, session_id: str, sender: str, message: str, meta: Optional[Dict[str, Any]] = None) -> int:
        cur = self._conn.cursor()
        created_at = datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO chats(created_at, session_id, sender, message, meta) VALUES(?,?,?,?,?)",
            (created_at, session_id, sender, message, json.dumps(meta or {})),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def get_chat_history(self, session_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, created_at, session_id, sender, message, meta FROM chats WHERE session_id = ? ORDER BY id ASC LIMIT ?",
            (session_id, limit),
        )
        rows = cur.fetchall()
        history: List[Dict[str, Any]] = []
        for r in rows:
            item = dict(r)
            try:
                item["meta"] = json.loads(item.get("meta") or "{}")
            except Exception:
                item["meta"] = {}
            history.append(item)
        return history

    def get_recent_chats(self, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, created_at, session_id, sender, message FROM chats ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    # Unanswered queue
    def enqueue_unanswered(self, question: str) -> int:
        cur = self._conn.cursor()
        created_at = datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO unanswered(created_at, question, status) VALUES(?,?, 'pending')",
            (created_at, question),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def get_pending_unanswered(self, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, created_at, question, status, answer FROM unanswered WHERE status = 'pending' ORDER BY id ASC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]

    def mark_unanswered_answered(self, qa_id: int, answer: str) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "UPDATE unanswered SET status = 'answered', answer = ? WHERE id = ?",
            (answer, qa_id),
        )
        self._conn.commit()

    # Scan logs
    def add_scan_log(self, status: str, findings: Optional[Dict[str, Any]] = None, started_at: Optional[str] = None, ended_at: Optional[str] = None) -> int:
        cur = self._conn.cursor()
        _started_at = started_at or datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO scans(started_at, ended_at, status, findings) VALUES(?,?,?,?)",
            (_started_at, ended_at, status, json.dumps(findings or {})),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def update_scan_log(self, scan_id: int, status: Optional[str] = None, findings: Optional[Dict[str, Any]] = None, ended_at: Optional[str] = None) -> None:
        cur = self._conn.cursor()
        existing = self._conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
        if not existing:
            return
        new_status = status or existing["status"]
        new_findings = json.dumps(findings or json.loads(existing["findings"] or "{}"))
        new_ended_at = ended_at or existing["ended_at"]
        cur.execute(
            "UPDATE scans SET ended_at = ?, status = ?, findings = ? WHERE id = ?",
            (new_ended_at, new_status, new_findings, scan_id),
        )
        self._conn.commit()

    def get_recent_scans(self, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, started_at, ended_at, status, findings FROM scans ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        result: List[Dict[str, Any]] = []
        for r in rows:
            item = dict(r)
            try:
                item["findings"] = json.loads(item.get("findings") or "{}")
            except Exception:
                item["findings"] = {}
            result.append(item)
        return result

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass