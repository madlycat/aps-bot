from __future__ import annotations

import sqlite3
from pathlib import Path


class ConfigStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS enabled_channels (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                enabled_by INTEGER,
                enabled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._connection.commit()

    def enable(self, channel_id: int, guild_id: int, enabled_by: int | None = None) -> None:
        self._connection.execute(
            """INSERT INTO enabled_channels(channel_id, guild_id, enabled_by)
               VALUES (?, ?, ?)
               ON CONFLICT(channel_id) DO UPDATE SET
                   guild_id=excluded.guild_id, enabled_by=excluded.enabled_by""",
            (channel_id, guild_id, enabled_by),
        )
        self._connection.commit()

    def disable(self, channel_id: int) -> bool:
        cursor = self._connection.execute(
            "DELETE FROM enabled_channels WHERE channel_id = ?", (channel_id,)
        )
        self._connection.commit()
        return cursor.rowcount > 0

    def is_enabled(self, channel_id: int) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM enabled_channels WHERE channel_id = ?", (channel_id,)
        ).fetchone()
        return row is not None

    def channels_for_guild(self, guild_id: int) -> list[int]:
        rows = self._connection.execute(
            "SELECT channel_id FROM enabled_channels WHERE guild_id = ? ORDER BY channel_id",
            (guild_id,),
        ).fetchall()
        return [row[0] for row in rows]

    def close(self) -> None:
        self._connection.close()

