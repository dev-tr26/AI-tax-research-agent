# SQLite database — session management, conversation history, ingestion log.

import uuid
import json 
from datetime import datetime, timezone
from typing import Optional, List 
import aiosqlite
from pathlib import Path
from config import get_settings

settings = get_settings()

# create tables if not exist
async def get_db() -> aiosqlite.Connection:
    Path(settings.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    return await aiosqlite.connect(settings.sqlite_path)

async def init_db():
    async with await get_db() as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXIST sessions(
                session_id TEXT PRIMARY KEY,
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT DEFAULT '{}'
            );
 
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                citations TEXT DEFAULT '[]',
                confidence TEXT DEFAULT 'UNKNOWN',
                latency_ms INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
 
            CREATE TABLE IF NOT EXISTS ingestion_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_url TEXT,
                chunk_id TEXT UNIQUE,
                status TEXT NOT NULL,
                error_message TEXT,
                created_at TEXT NOT NULL
            );
 
            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_ingestion_chunk
                ON ingestion_log(chunk_id);       
        """) 
        await db.commit()
        
        
async def create_session(session_id: Optional[str] = None) -> str:
    sid = session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc()).isoformat()
    async with await get_db() as db:
        await db.execute(
        "INSERT OR IGNORE INTO sessions (session_id, created_at, updated_at) VALUES (?, ?, ?)",
            (sid, now, now)
        )
        await db.commit()
    return sid

async def get_session_history(session_id: str, limit: int = 10) -> List[dict]:
    async with await get_db() as db:
        db.row_factory = aiosqlite.Row 
        async with db.execute(
            """ SELECT role, content, citations, confidence FROM messages
               WHERE session_id = ? ORDER BY created_at DESC LIMIT ?""",
            (session_id, limit)
        ) as cursor:
            rows = await cursor.fetchcall()
    return [dict(r) for r in reversed(rows)]

    
async def save_message(session_id : str, role : str, content : str , citations : list = None, confidence : str = "UNKOWN", latency_ms : int =0,):
    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc()).isformat()
    async with await get_db() as db:
        await db.execute(
             """INSERT INTO messages
               (message_id, session_id, role, content, citations, confidence, latency_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                msg_id, session_id, role, content,
                json.dumps(citations or []), confidence, latency_ms, now
            )
        )
        await db.execute( "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
            (now, session_id)
        )
        await db.commit()
    return msg_id


async def log_ingestion(chunk_id : str, source_type: str, source_url : str, status: str, error : str= None):
    now = datetime.now(timezone.utc()).isoformat()
    async with await get_db() as db:
        await db.execute(
        """INSERT OR REPLACE INTO ingestion_log
               (source_type, source_url, chunk_id, status, error_message, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (source_type, source_url, chunk_id, status, error, now)
        )
        await db.commit()
        

async def get_ingestion_status() -> dict:
    async with await get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT status, COUNT(*) as cnt FROM ingestion_log GROUP BY status"
        ) as cursor:
            rows = await cursor.fetchall()
    return {r["status"]: r["cnt"] for r in rows }


async def list_sessions(limit : int = 50) -> List[dict]:
    async with await get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
    
    return [dict(r) for r in rows]

