# APS Bot

A standalone Discord replacement for a YAGPDB APS feature. Messages in configured channels are recreated through a bot-owned webhook with the member's display name and avatar, producing a native-looking message instead of an embed.

## What it supports

- Plain webhook messages—no custom embeds and automatic link embeds are suppressed
- Images, video, audio, documents, spoiler files, attachment descriptions, and stickers
- Posts longer than Discord's 2,000-character limit and more than 10 media files
- Public and private threads beneath an enabled channel
- Persistent per-server configuration with `/aps enable`, `/aps disable`, and `/aps status`
- Safe delivery order: media is downloaded and the webhook post is sent before the source is deleted
- Per-channel ordering and automatic rollback if part of a multi-message upload fails
- Docker Compose or direct Python deployment

Mentions are rendered but deliberately do not ping a second time when the webhook copy is created.

## Discord setup

1. Create an application and bot in the [Discord Developer Portal](https://discord.com/developers/applications).
2. On the bot page, enable the **Message Content Intent**.
3. Under OAuth2 URL Generator, select `bot` and `applications.commands`.
4. Give the bot these server permissions:
   - View Channels
   - Send Messages
   - Send Messages in Threads
   - Manage Messages
   - Manage Webhooks
   - Attach Files
   - Read Message History
5. Invite it to the server.

Do not grant Administrator; it is unnecessary.

## Run with Docker

```sh
cp .env.example .env
# Put the bot token in .env
docker compose up -d --build
```

Then run `/aps enable` in each target channel. Use `/aps status` to see the current configuration.

## Run with Python

Python 3.11 or newer is required.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pip install -e . --no-deps
cp .env.example .env
```

Load the values from `.env` in your process manager, then run:

```sh
python -m aps_bot
```

The bot intentionally does not parse `.env` itself. Docker Compose loads it automatically; for a direct deployment, configure these variables in your shell or process manager.

## Environment variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `DISCORD_TOKEN` | Yes | Discord bot token |
| `DISCORD_GUILD_ID` | No | Development server for instant slash-command sync |
| `APS_DATABASE_PATH` | No | SQLite path; defaults to `data/aps.db` |
| `APS_BOOTSTRAP_CHANNEL_IDS` | No | Comma-separated channels enabled on first connection |
| `APS_WEBHOOK_NAME` | No | Bot-owned webhook name; defaults to `APS Relay` |

Global slash commands can take up to an hour to appear. Set `DISCORD_GUILD_ID` while testing for immediate registration.

## Important behavior

Discord webhooks cannot preserve Discord's native reply reference. Ordinary text and media are seamless, but a relayed reply becomes an independent webhook message. Failed webhook sends leave the original message intact so content is never silently lost.

## Development

```sh
pip install -r requirements-dev.txt
ruff check .
pytest
```

## License

MIT
