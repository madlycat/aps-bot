from __future__ import annotations

import logging

import discord
from discord import app_commands

from .config import Settings
from .relay import RelayService
from .store import ConfigStore

logger = logging.getLogger(__name__)


class APSBot(discord.Client):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.settings = settings
        self.tree = app_commands.CommandTree(self)
        self.store = ConfigStore(settings.database_path)
        self.relay_service = RelayService(self, settings.webhook_name)
        self.aps = app_commands.Group(name="aps", description="Configure APS relay channels")
        self._bootstrapped = False
        self._register_commands()

    def _register_commands(self) -> None:
        @self.aps.command(name="enable", description="Enable seamless APS posts in a channel")
        @app_commands.default_permissions(manage_channels=True)
        @app_commands.checks.has_permissions(manage_channels=True)
        async def enable(
            interaction: discord.Interaction,
            channel: discord.TextChannel | None = None,
        ) -> None:
            if interaction.guild is None:
                await interaction.response.send_message(
                    "This command only works in a server.", ephemeral=True
                )
                return
            target = channel or interaction.channel
            if not isinstance(target, discord.TextChannel):
                await interaction.response.send_message(
                    "Choose a regular text channel.", ephemeral=True
                )
                return
            permissions = target.permissions_for(interaction.guild.me)
            needed = [
                name
                for name, present in (
                    ("Manage Webhooks", permissions.manage_webhooks),
                    ("Manage Messages", permissions.manage_messages),
                    ("View Channel", permissions.view_channel),
                    ("Send Messages", permissions.send_messages),
                    ("Attach Files", permissions.attach_files),
                )
                if not present
            ]
            if needed:
                await interaction.response.send_message(
                    "I still need: " + ", ".join(needed) + ".", ephemeral=True
                )
                return
            self.store.enable(target.id, interaction.guild.id, interaction.user.id)
            await interaction.response.send_message(
                f"APS is enabled in {target.mention}.", ephemeral=True
            )

        @self.aps.command(name="disable", description="Disable APS posts in a channel")
        @app_commands.default_permissions(manage_channels=True)
        @app_commands.checks.has_permissions(manage_channels=True)
        async def disable(
            interaction: discord.Interaction,
            channel: discord.TextChannel | None = None,
        ) -> None:
            target = channel or interaction.channel
            if not isinstance(target, discord.TextChannel):
                await interaction.response.send_message(
                    "Choose a regular text channel.", ephemeral=True
                )
                return
            removed = self.store.disable(target.id)
            status = "disabled" if removed else "was not enabled"
            await interaction.response.send_message(
                f"APS {status} in {target.mention}.", ephemeral=True
            )

        @self.aps.command(name="status", description="List this server's APS channels")
        @app_commands.default_permissions(manage_channels=True)
        @app_commands.checks.has_permissions(manage_channels=True)
        async def status(interaction: discord.Interaction) -> None:
            if interaction.guild is None:
                await interaction.response.send_message(
                    "This command only works in a server.", ephemeral=True
                )
                return
            channel_ids = self.store.channels_for_guild(interaction.guild.id)
            text = (
                ", ".join(f"<#{channel_id}>" for channel_id in channel_ids)
                or "No channels enabled."
            )
            await interaction.response.send_message(text, ephemeral=True)

        self.tree.add_command(self.aps)

        @self.tree.error
        async def on_app_command_error(
            interaction: discord.Interaction,
            error: app_commands.AppCommandError,
        ) -> None:
            if isinstance(error, app_commands.MissingPermissions):
                text = "You need Manage Channels to configure APS."
            else:
                logger.exception("Application command failed", exc_info=error)
                text = "APS could not complete that command. Check the bot logs."
            if interaction.response.is_done():
                await interaction.followup.send(text, ephemeral=True)
            else:
                await interaction.response.send_message(text, ephemeral=True)

    async def setup_hook(self) -> None:
        if self.settings.guild_id is not None:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info("Synced commands to development guild %s", self.settings.guild_id)
        else:
            await self.tree.sync()
            logger.info("Synced global commands")

    async def on_ready(self) -> None:
        if not self._bootstrapped:
            for channel_id in self.settings.bootstrap_channel_ids:
                channel = self.get_channel(channel_id)
                if isinstance(channel, discord.TextChannel):
                    self.store.enable(channel.id, channel.guild.id)
                else:
                    logger.warning("Bootstrap channel %s was not found", channel_id)
            self._bootstrapped = True
        logger.info("Ready as %s (%s)", self.user, self.user.id if self.user else "unknown")

    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.webhook_id is not None or message.author.bot:
            return
        configured_id = (
            message.channel.parent_id
            if isinstance(message.channel, discord.Thread)
            else message.channel.id
        )
        if not self.store.is_enabled(configured_id):
            return
        try:
            await self.relay_service.relay(message)
        except discord.Forbidden:
            logger.exception("Missing permissions while relaying message %s", message.id)
        except discord.HTTPException:
            logger.exception("Discord rejected relay for message %s", message.id)

    async def close(self) -> None:
        self.store.close()
        await super().close()
