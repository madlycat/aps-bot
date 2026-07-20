from __future__ import annotations

import asyncio
import io
import logging
from dataclasses import dataclass

import discord

logger = logging.getLogger(__name__)


def split_content(content: str, limit: int = 2000) -> list[str]:
    """Split Discord content without losing characters, preferring line boundaries."""
    if not content:
        return []
    chunks: list[str] = []
    remaining = content
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit + 1)
        if split_at <= 0:
            split_at = limit
        else:
            split_at += 1
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:]
    if remaining:
        chunks.append(remaining)
    return chunks


@dataclass(slots=True)
class BufferedUpload:
    data: bytes
    filename: str
    description: str | None = None
    spoiler: bool = False

    def to_discord_file(self) -> discord.File:
        return discord.File(
            io.BytesIO(self.data),
            filename=self.filename,
            description=self.description,
            spoiler=self.spoiler,
        )


class RelayService:
    def __init__(self, bot: discord.Client, webhook_name: str) -> None:
        self.bot = bot
        self.webhook_name = webhook_name
        self._webhooks: dict[int, discord.Webhook] = {}
        self._channel_locks: dict[int, asyncio.Lock] = {}

    async def _buffer_media(self, message: discord.Message) -> list[BufferedUpload]:
        uploads: list[BufferedUpload] = []
        for attachment in message.attachments:
            uploads.append(
                BufferedUpload(
                    data=await attachment.read(use_cached=True),
                    filename=attachment.filename,
                    description=attachment.description,
                    spoiler=attachment.is_spoiler(),
                )
            )

        for sticker in message.stickers:
            try:
                data = await sticker.read()
            except (discord.HTTPException, discord.NotFound):
                logger.warning("Could not download sticker %s", sticker.id)
                continue
            extension = {
                discord.StickerFormatType.png: "png",
                discord.StickerFormatType.apng: "png",
                discord.StickerFormatType.lottie: "json",
                discord.StickerFormatType.gif: "gif",
            }.get(sticker.format, "bin")
            uploads.append(BufferedUpload(data=data, filename=f"{sticker.name}.{extension}"))
        return uploads

    async def _webhook_for(self, channel: discord.TextChannel) -> discord.Webhook:
        cached = self._webhooks.get(channel.id)
        if cached is not None:
            return cached

        me = self.bot.user
        webhooks = await channel.webhooks()
        webhook = next(
            (
                item
                for item in webhooks
                if item.name == self.webhook_name
                and item.user is not None
                and me is not None
                and item.user.id == me.id
            ),
            None,
        )
        if webhook is None:
            webhook = await channel.create_webhook(
                name=self.webhook_name,
                reason="APS standalone relay",
            )
        self._webhooks[channel.id] = webhook
        return webhook

    async def relay(self, message: discord.Message) -> None:
        """Relay one message while preserving the channel's original message order."""
        lock = self._channel_locks.setdefault(message.channel.id, asyncio.Lock())
        async with lock:
            await self._relay_locked(message)

    async def _relay_locked(self, message: discord.Message) -> None:
        destination: discord.TextChannel
        thread: discord.Thread | None = None
        if isinstance(message.channel, discord.Thread):
            parent = message.channel.parent
            if not isinstance(parent, discord.TextChannel):
                return
            destination = parent
            thread = message.channel
        elif isinstance(message.channel, discord.TextChannel):
            destination = message.channel
        else:
            return

        # Buffer first: attachment CDN access can disappear after the source is deleted.
        uploads = await self._buffer_media(message)
        webhook = await self._webhook_for(destination)
        chunks = split_content(message.content)
        upload_batches = [uploads[index : index + 10] for index in range(0, len(uploads), 10)]
        if not chunks and not upload_batches:
            logger.warning("Message %s had no relayable text or media", message.id)
            return
        send_count = max(len(chunks), len(upload_batches), 1)
        username = message.author.display_name[:80]
        avatar_url = message.author.display_avatar.url

        sent_messages: list[discord.WebhookMessage] = []
        try:
            for index in range(send_count):
                content = chunks[index] if index < len(chunks) else None
                files = (
                    [upload.to_discord_file() for upload in upload_batches[index]]
                    if index < len(upload_batches)
                    else None
                )
                sent = await webhook.send(
                    content=content,
                    username=username,
                    avatar_url=avatar_url,
                    files=files,
                    allowed_mentions=discord.AllowedMentions.none(),
                    suppress_embeds=True,
                    wait=True,
                    thread=thread,
                )
                sent_messages.append(sent)
        except discord.HTTPException:
            # A multi-part relay should be all-or-nothing. Keep the user's source
            # message and remove any webhook chunks that were already accepted.
            self._webhooks.pop(destination.id, None)
            for sent in reversed(sent_messages):
                try:
                    await sent.delete()
                except discord.HTTPException:
                    logger.warning("Could not roll back webhook message %s", sent.id)
            raise

        await message.delete()
