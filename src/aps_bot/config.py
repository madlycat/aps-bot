from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _optional_int(name: str) -> int | None:
    value = os.getenv(name, "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a Discord snowflake (an integer)") from exc


def _channel_ids() -> tuple[int, ...]:
    value = os.getenv("APS_BOOTSTRAP_CHANNEL_IDS", "")
    try:
        return tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise RuntimeError(
            "APS_BOOTSTRAP_CHANNEL_IDS must contain comma-separated integers"
        ) from exc


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    database_path: Path
    guild_id: int | None
    bootstrap_channel_ids: tuple[int, ...]
    webhook_name: str

    @classmethod
    def from_env(cls) -> Settings:
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise RuntimeError("DISCORD_TOKEN is required")
        return cls(
            token=token,
            database_path=Path(os.getenv("APS_DATABASE_PATH", "data/aps.db")),
            guild_id=_optional_int("DISCORD_GUILD_ID"),
            bootstrap_channel_ids=_channel_ids(),
            webhook_name=os.getenv("APS_WEBHOOK_NAME", "APS Relay").strip() or "APS Relay",
        )
