from pathlib import Path

from aps_bot.store import ConfigStore


def test_enable_list_and_disable(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "aps.db")
    try:
        store.enable(channel_id=20, guild_id=1, enabled_by=99)
        store.enable(channel_id=10, guild_id=1, enabled_by=99)
        store.enable(channel_id=30, guild_id=2, enabled_by=99)

        assert store.is_enabled(20)
        assert store.channels_for_guild(1) == [10, 20]
        assert store.disable(20)
        assert not store.is_enabled(20)
        assert not store.disable(20)
    finally:
        store.close()


def test_enabling_twice_updates_without_duplicates(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "aps.db")
    try:
        store.enable(channel_id=10, guild_id=1, enabled_by=1)
        store.enable(channel_id=10, guild_id=1, enabled_by=2)
        assert store.channels_for_guild(1) == [10]
    finally:
        store.close()

