"""
Cog de notifications Discord pour le bot Minecraft.

Ce module gère les notifications automatiques pour différents événements
du serveur Minecraft vers les channels Discord configurés.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Literal, Dict, Any, Callable
from datetime import datetime
from enum import Enum
import asyncio


class NotificationType(Enum):
    """Types de notifications disponibles."""
    PLAYER_JOIN = "player_join"
    PLAYER_LEAVE = "player_leave"
    PLAYER_DEATH = "player_death"
    PLAYER_ACHIEVEMENT = "player_achievement"
    CHAT_RELAY = "chat_relay"
    SERVER_STATUS = "server_status"
    PERFORMANCE_ALERT = "performance_alert"


# Couleurs pour chaque type de notification
NOTIFICATION_COLORS: Dict[NotificationType, discord.Color] = {
    NotificationType.PLAYER_JOIN: discord.Color.green(),
    NotificationType.PLAYER_LEAVE: discord.Color.orange(),
    NotificationType.PLAYER_DEATH: discord.Color.red(),
    NotificationType.PLAYER_ACHIEVEMENT: discord.Color.gold(),
    NotificationType.CHAT_RELAY: discord.Color.blue(),
    NotificationType.SERVER_STATUS: discord.Color.purple(),
    NotificationType.PERFORMANCE_ALERT: discord.Color.dark_red(),
}

# Emojis pour chaque type de notification
NOTIFICATION_EMOJIS: Dict[NotificationType, str] = {
    NotificationType.PLAYER_JOIN: "\u2705",
    NotificationType.PLAYER_LEAVE: "\u274c",
    NotificationType.PLAYER_DEATH: "\u2620\ufe0f",
    NotificationType.PLAYER_ACHIEVEMENT: "\u2b50",
    NotificationType.CHAT_RELAY: "\u2709\ufe0f",
    NotificationType.SERVER_STATUS: "\U0001f5a5\ufe0f",
    NotificationType.PERFORMANCE_ALERT: "\u26a0\ufe0f",
}

# Descriptions des types de notifications
NOTIFICATION_DESCRIPTIONS: Dict[NotificationType, str] = {
    NotificationType.PLAYER_JOIN: "Connexion d'un joueur sur le serveur",
    NotificationType.PLAYER_LEAVE: "Déconnexion d'un joueur du serveur",
    NotificationType.PLAYER_DEATH: "Mort d'un joueur avec la cause",
    NotificationType.PLAYER_ACHIEVEMENT: "Obtention d'un succès/advancement",
    NotificationType.CHAT_RELAY: "Messages du chat in-game",
    NotificationType.SERVER_STATUS: "Statut du serveur (Online/Offline/Crash)",
    NotificationType.PERFORMANCE_ALERT: "Alertes de performance (TPS/RAM/CPU)",
}

# Choix pour les commandes slash
NOTIFICATION_TYPE_CHOICES = [
    app_commands.Choice(name="Connexion joueur", value="player_join"),
    app_commands.Choice(name="Déconnexion joueur", value="player_leave"),
    app_commands.Choice(name="Mort joueur", value="player_death"),
    app_commands.Choice(name="Succès/Achievement", value="player_achievement"),
    app_commands.Choice(name="Relay chat", value="chat_relay"),
    app_commands.Choice(name="Statut serveur", value="server_status"),
    app_commands.Choice(name="Alerte performance", value="performance_alert"),
]


class NotificationConfig:
    """Classe pour gérer la configuration des notifications."""

    def __init__(self, guild_id: int, notification_type: NotificationType):
        self.guild_id = guild_id
        self.notification_type = notification_type
        self.enabled: bool = False
        self.channel_id: Optional[int] = None
        self.custom_message: Optional[str] = None
        self.mention_role_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convertit la configuration en dictionnaire pour la DB."""
        return {
            "guild_id": self.guild_id,
            "notification_type": self.notification_type.value,
            "enabled": self.enabled,
            "channel_id": self.channel_id,
            "custom_message": self.custom_message,
            "mention_role_id": self.mention_role_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationConfig":
        """Crée une configuration depuis un dictionnaire de la DB."""
        config = cls(
            guild_id=data["guild_id"],
            notification_type=NotificationType(data["notification_type"])
        )
        config.enabled = data.get("enabled", False)
        config.channel_id = data.get("channel_id")
        config.custom_message = data.get("custom_message")
        config.mention_role_id = data.get("mention_role_id")
        return config


class ConfigurationView(discord.ui.View):
    """Vue interactive pour la configuration des notifications."""

    def __init__(self, cog: "NotificationsCog", guild_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id
        self.current_type: Optional[NotificationType] = None

    @discord.ui.select(
        placeholder="Sélectionnez un type de notification...",
        options=[
            discord.SelectOption(
                label="Connexion joueur",
                value="player_join",
                emoji="\u2705",
                description="Notifications de connexion"
            ),
            discord.SelectOption(
                label="Déconnexion joueur",
                value="player_leave",
                emoji="\u274c",
                description="Notifications de déconnexion"
            ),
            discord.SelectOption(
                label="Mort joueur",
                value="player_death",
                emoji="\u2620\ufe0f",
                description="Notifications de mort"
            ),
            discord.SelectOption(
                label="Succès/Achievement",
                value="player_achievement",
                emoji="\u2b50",
                description="Notifications de succès"
            ),
            discord.SelectOption(
                label="Relay chat",
                value="chat_relay",
                emoji="\u2709\ufe0f",
                description="Messages du chat in-game"
            ),
            discord.SelectOption(
                label="Statut serveur",
                value="server_status",
                emoji="\U0001f5a5\ufe0f",
                description="Statut Online/Offline/Crash"
            ),
            discord.SelectOption(
                label="Alerte performance",
                value="performance_alert",
                emoji="\u26a0\ufe0f",
                description="Alertes TPS/RAM/CPU"
            ),
        ]
    )
    async def select_notification_type(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        """Gère la sélection du type de notification."""
        self.current_type = NotificationType(select.values[0])
        config = await self.cog.get_notification_config(
            self.guild_id, self.current_type
        )

        embed = self._create_config_embed(config)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Activer", style=discord.ButtonStyle.green, row=1)
    async def enable_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Active la notification sélectionnée."""
        if not self.current_type:
            await interaction.response.send_message(
                "Veuillez d'abord sélectionner un type de notification.",
                ephemeral=True
            )
            return

        await self.cog.set_notification_enabled(
            self.guild_id, self.current_type, True
        )
        config = await self.cog.get_notification_config(
            self.guild_id, self.current_type
        )
        embed = self._create_config_embed(config)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Désactiver", style=discord.ButtonStyle.red, row=1)
    async def disable_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Désactive la notification sélectionnée."""
        if not self.current_type:
            await interaction.response.send_message(
                "Veuillez d'abord sélectionner un type de notification.",
                ephemeral=True
            )
            return

        await self.cog.set_notification_enabled(
            self.guild_id, self.current_type, False
        )
        config = await self.cog.get_notification_config(
            self.guild_id, self.current_type
        )
        embed = self._create_config_embed(config)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Tester", style=discord.ButtonStyle.blurple, row=1)
    async def test_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Teste la notification sélectionnée."""
        if not self.current_type:
            await interaction.response.send_message(
                "Veuillez d'abord sélectionner un type de notification.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        success = await self.cog.send_test_notification(
            self.guild_id, self.current_type
        )

        if success:
            await interaction.followup.send(
                f"Notification de test envoyée pour **{self.current_type.value}**!",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "Impossible d'envoyer la notification. Vérifiez que le channel est configuré.",
                ephemeral=True
            )

    def _create_config_embed(self, config: NotificationConfig) -> discord.Embed:
        """Crée un embed affichant la configuration actuelle."""
        notif_type = config.notification_type
        color = NOTIFICATION_COLORS[notif_type]
        emoji = NOTIFICATION_EMOJIS[notif_type]
        description = NOTIFICATION_DESCRIPTIONS[notif_type]

        embed = discord.Embed(
            title=f"{emoji} Configuration: {notif_type.value}",
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )

        status = "\u2705 Activée" if config.enabled else "\u274c Désactivée"
        embed.add_field(name="Statut", value=status, inline=True)

        channel_text = f"<#{config.channel_id}>" if config.channel_id else "Non configuré"
        embed.add_field(name="Channel", value=channel_text, inline=True)

        if config.mention_role_id:
            embed.add_field(
                name="Rôle mentionné",
                value=f"<@&{config.mention_role_id}>",
                inline=True
            )

        return embed


class NotificationsCog(commands.Cog):
    """Cog pour gérer les notifications Discord du serveur Minecraft."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._configs: Dict[int, Dict[NotificationType, NotificationConfig]] = {}
        self._log_parser_callbacks: Dict[str, Callable] = {}

    async def cog_load(self):
        """Appelé quand le cog est chargé."""
        await self._load_configs_from_db()
        self._register_log_parser_listeners()

    async def cog_unload(self):
        """Appelé quand le cog est déchargé."""
        self._unregister_log_parser_listeners()

    # =========================================================================
    # Gestion de la base de données
    # =========================================================================

    async def _load_configs_from_db(self):
        """Charge les configurations depuis la base de données."""
        db = getattr(self.bot, 'database', None)
        if not db:
            return

        try:
            configs = await db.fetch_all("notification_configs")
            for config_data in configs:
                config = NotificationConfig.from_dict(config_data)
                guild_id = config.guild_id

                if guild_id not in self._configs:
                    self._configs[guild_id] = {}

                self._configs[guild_id][config.notification_type] = config
        except Exception as e:
            print(f"Erreur lors du chargement des configurations: {e}")

    async def _save_config_to_db(self, config: NotificationConfig):
        """Sauvegarde une configuration dans la base de données."""
        db = getattr(self.bot, 'database', None)
        if not db:
            return

        try:
            await db.upsert(
                "notification_configs",
                config.to_dict(),
                unique_keys=["guild_id", "notification_type"]
            )
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de la configuration: {e}")

    async def get_notification_config(
        self, guild_id: int, notif_type: NotificationType
    ) -> NotificationConfig:
        """Récupère la configuration d'une notification pour un serveur."""
        if guild_id not in self._configs:
            self._configs[guild_id] = {}

        if notif_type not in self._configs[guild_id]:
            self._configs[guild_id][notif_type] = NotificationConfig(
                guild_id, notif_type
            )

        return self._configs[guild_id][notif_type]

    async def set_notification_enabled(
        self, guild_id: int, notif_type: NotificationType, enabled: bool
    ):
        """Active ou désactive une notification."""
        config = await self.get_notification_config(guild_id, notif_type)
        config.enabled = enabled
        await self._save_config_to_db(config)

    async def set_notification_channel(
        self, guild_id: int, notif_type: NotificationType, channel_id: int
    ):
        """Définit le channel pour une notification."""
        config = await self.get_notification_config(guild_id, notif_type)
        config.channel_id = channel_id
        await self._save_config_to_db(config)

    # =========================================================================
    # Création des embeds de notification
    # =========================================================================

    def _create_player_join_embed(
        self, player_name: str, **kwargs
    ) -> discord.Embed:
        """Crée un embed pour la connexion d'un joueur."""
        embed = discord.Embed(
            title=f"{NOTIFICATION_EMOJIS[NotificationType.PLAYER_JOIN]} Joueur connecté",
            description=f"**{player_name}** a rejoint le serveur!",
            color=NOTIFICATION_COLORS[NotificationType.PLAYER_JOIN],
            timestamp=datetime.utcnow()
        )

        if "player_count" in kwargs:
            embed.add_field(
                name="Joueurs en ligne",
                value=str(kwargs["player_count"]),
                inline=True
            )

        embed.set_footer(text="Minecraft Server")
        return embed

    def _create_player_leave_embed(
        self, player_name: str, **kwargs
    ) -> discord.Embed:
        """Crée un embed pour la déconnexion d'un joueur."""
        embed = discord.Embed(
            title=f"{NOTIFICATION_EMOJIS[NotificationType.PLAYER_LEAVE]} Joueur déconnecté",
            description=f"**{player_name}** a quitté le serveur.",
            color=NOTIFICATION_COLORS[NotificationType.PLAYER_LEAVE],
            timestamp=datetime.utcnow()
        )

        if "play_time" in kwargs:
            embed.add_field(
                name="Temps de jeu",
                value=kwargs["play_time"],
                inline=True
            )

        if "player_count" in kwargs:
            embed.add_field(
                name="Joueurs en ligne",
                value=str(kwargs["player_count"]),
                inline=True
            )

        embed.set_footer(text="Minecraft Server")
        return embed

    def _create_player_death_embed(
        self, player_name: str, death_message: str, **kwargs
    ) -> discord.Embed:
        """Crée un embed pour la mort d'un joueur."""
        embed = discord.Embed(
            title=f"{NOTIFICATION_EMOJIS[NotificationType.PLAYER_DEATH]} Mort d'un joueur",
            description=death_message,
            color=NOTIFICATION_COLORS[NotificationType.PLAYER_DEATH],
            timestamp=datetime.utcnow()
        )

        embed.add_field(name="Joueur", value=player_name, inline=True)

        if "killer" in kwargs:
            embed.add_field(name="Tué par", value=kwargs["killer"], inline=True)

        if "weapon" in kwargs:
            embed.add_field(name="Arme", value=kwargs["weapon"], inline=True)

        embed.set_footer(text="Minecraft Server")
        return embed

    def _create_achievement_embed(
        self, player_name: str, achievement: str, **kwargs
    ) -> discord.Embed:
        """Crée un embed pour un succès obtenu."""
        embed = discord.Embed(
            title=f"{NOTIFICATION_EMOJIS[NotificationType.PLAYER_ACHIEVEMENT]} Succès débloqué!",
            description=f"**{player_name}** a obtenu le succès:",
            color=NOTIFICATION_COLORS[NotificationType.PLAYER_ACHIEVEMENT],
            timestamp=datetime.utcnow()
        )

        embed.add_field(name="Succès", value=achievement, inline=False)

        if "description" in kwargs:
            embed.add_field(
                name="Description",
                value=kwargs["description"],
                inline=False
            )

        embed.set_footer(text="Minecraft Server")
        return embed

    def _create_chat_relay_embed(
        self, player_name: str, message: str, **kwargs
    ) -> discord.Embed:
        """Crée un embed pour un message du chat."""
        embed = discord.Embed(
            description=f"**{player_name}**: {message}",
            color=NOTIFICATION_COLORS[NotificationType.CHAT_RELAY],
            timestamp=datetime.utcnow()
        )

        embed.set_footer(text="Chat Minecraft")
        return embed

    def _create_server_status_embed(
        self, status: str, **kwargs
    ) -> discord.Embed:
        """Crée un embed pour le statut du serveur."""
        status_lower = status.lower()

        if status_lower == "online":
            title = "\U0001f7e2 Serveur en ligne"
            description = "Le serveur Minecraft est maintenant **en ligne**!"
        elif status_lower == "offline":
            title = "\U0001f534 Serveur hors ligne"
            description = "Le serveur Minecraft est maintenant **hors ligne**."
        elif status_lower == "crash":
            title = "\u26a0\ufe0f Crash du serveur"
            description = "Le serveur Minecraft a **crashé**!"
        else:
            title = f"\U0001f5a5\ufe0f Statut: {status}"
            description = f"Statut du serveur: **{status}**"

        embed = discord.Embed(
            title=title,
            description=description,
            color=NOTIFICATION_COLORS[NotificationType.SERVER_STATUS],
            timestamp=datetime.utcnow()
        )

        if "uptime" in kwargs:
            embed.add_field(name="Uptime", value=kwargs["uptime"], inline=True)

        if "reason" in kwargs:
            embed.add_field(name="Raison", value=kwargs["reason"], inline=False)

        embed.set_footer(text="Minecraft Server")
        return embed

    def _create_performance_alert_embed(
        self, alert_type: str, value: float, threshold: float, **kwargs
    ) -> discord.Embed:
        """Crée un embed pour une alerte de performance."""
        embed = discord.Embed(
            title=f"{NOTIFICATION_EMOJIS[NotificationType.PERFORMANCE_ALERT]} Alerte Performance",
            color=NOTIFICATION_COLORS[NotificationType.PERFORMANCE_ALERT],
            timestamp=datetime.utcnow()
        )

        alert_type_upper = alert_type.upper()

        if alert_type_upper == "TPS":
            embed.description = f"Le TPS du serveur est **critique**!"
            embed.add_field(name="TPS actuel", value=f"{value:.1f}", inline=True)
            embed.add_field(name="Seuil", value=f"< {threshold:.1f}", inline=True)
        elif alert_type_upper == "RAM":
            embed.description = f"L'utilisation de la RAM est **élevée**!"
            embed.add_field(
                name="RAM utilisée",
                value=f"{value:.1f}%",
                inline=True
            )
            embed.add_field(name="Seuil", value=f"> {threshold:.1f}%", inline=True)
        elif alert_type_upper == "CPU":
            embed.description = f"L'utilisation du CPU est **élevée**!"
            embed.add_field(
                name="CPU utilisé",
                value=f"{value:.1f}%",
                inline=True
            )
            embed.add_field(name="Seuil", value=f"> {threshold:.1f}%", inline=True)
        else:
            embed.description = f"Alerte: **{alert_type}**"
            embed.add_field(name="Valeur", value=str(value), inline=True)
            embed.add_field(name="Seuil", value=str(threshold), inline=True)

        embed.set_footer(text="Minecraft Server Monitor")
        return embed

    # =========================================================================
    # Envoi des notifications
    # =========================================================================

    async def send_notification(
        self,
        guild_id: int,
        notif_type: NotificationType,
        embed: discord.Embed,
        content: Optional[str] = None
    ) -> bool:
        """Envoie une notification dans le channel configuré."""
        config = await self.get_notification_config(guild_id, notif_type)

        if not config.enabled or not config.channel_id:
            return False

        channel = self.bot.get_channel(config.channel_id)
        if not channel:
            return False

        try:
            # Ajouter la mention du rôle si configuré
            if config.mention_role_id:
                content = f"<@&{config.mention_role_id}> {content or ''}"

            await channel.send(content=content, embed=embed)
            return True
        except discord.DiscordException as e:
            print(f"Erreur lors de l'envoi de la notification: {e}")
            return False

    async def send_test_notification(
        self, guild_id: int, notif_type: NotificationType
    ) -> bool:
        """Envoie une notification de test."""
        embed_creators = {
            NotificationType.PLAYER_JOIN: lambda: self._create_player_join_embed(
                "TestPlayer", player_count=5
            ),
            NotificationType.PLAYER_LEAVE: lambda: self._create_player_leave_embed(
                "TestPlayer", play_time="2h 30m", player_count=4
            ),
            NotificationType.PLAYER_DEATH: lambda: self._create_player_death_embed(
                "TestPlayer",
                "TestPlayer was slain by Zombie",
                killer="Zombie"
            ),
            NotificationType.PLAYER_ACHIEVEMENT: lambda: self._create_achievement_embed(
                "TestPlayer",
                "Getting an Upgrade",
                description="Construct a better pickaxe"
            ),
            NotificationType.CHAT_RELAY: lambda: self._create_chat_relay_embed(
                "TestPlayer", "Ceci est un message de test!"
            ),
            NotificationType.SERVER_STATUS: lambda: self._create_server_status_embed(
                "online", uptime="0h 0m"
            ),
            NotificationType.PERFORMANCE_ALERT: lambda: self._create_performance_alert_embed(
                "TPS", 15.5, 18.0
            ),
        }

        embed = embed_creators[notif_type]()
        embed.set_author(name="[TEST] Notification de test")

        return await self.send_notification(guild_id, notif_type, embed)

    # =========================================================================
    # Listeners pour le LogParser
    # =========================================================================

    def _register_log_parser_listeners(self):
        """Enregistre les listeners auprès du LogParser."""
        log_parser = getattr(self.bot, 'log_parser', None)
        if not log_parser:
            return

        # Définir les callbacks
        self._log_parser_callbacks = {
            "player_join": self._on_player_join,
            "player_leave": self._on_player_leave,
            "player_death": self._on_player_death,
            "player_achievement": self._on_player_achievement,
            "chat_message": self._on_chat_message,
            "server_status": self._on_server_status,
            "performance_alert": self._on_performance_alert,
        }

        # Enregistrer les callbacks
        for event_name, callback in self._log_parser_callbacks.items():
            if hasattr(log_parser, 'register_callback'):
                log_parser.register_callback(event_name, callback)

    def _unregister_log_parser_listeners(self):
        """Désenregistre les listeners du LogParser."""
        log_parser = getattr(self.bot, 'log_parser', None)
        if not log_parser:
            return

        for event_name, callback in self._log_parser_callbacks.items():
            if hasattr(log_parser, 'unregister_callback'):
                log_parser.unregister_callback(event_name, callback)

    async def _on_player_join(self, data: Dict[str, Any]):
        """Callback pour la connexion d'un joueur."""
        player_name = data.get("player_name", "Unknown")
        player_count = data.get("player_count")

        embed = self._create_player_join_embed(
            player_name, player_count=player_count
        )

        for guild_id in self._configs:
            await self.send_notification(
                guild_id, NotificationType.PLAYER_JOIN, embed
            )

    async def _on_player_leave(self, data: Dict[str, Any]):
        """Callback pour la déconnexion d'un joueur."""
        player_name = data.get("player_name", "Unknown")
        play_time = data.get("play_time")
        player_count = data.get("player_count")

        embed = self._create_player_leave_embed(
            player_name, play_time=play_time, player_count=player_count
        )

        for guild_id in self._configs:
            await self.send_notification(
                guild_id, NotificationType.PLAYER_LEAVE, embed
            )

    async def _on_player_death(self, data: Dict[str, Any]):
        """Callback pour la mort d'un joueur."""
        player_name = data.get("player_name", "Unknown")
        death_message = data.get("death_message", "Unknown cause")
        killer = data.get("killer")
        weapon = data.get("weapon")

        embed = self._create_player_death_embed(
            player_name, death_message, killer=killer, weapon=weapon
        )

        for guild_id in self._configs:
            await self.send_notification(
                guild_id, NotificationType.PLAYER_DEATH, embed
            )

    async def _on_player_achievement(self, data: Dict[str, Any]):
        """Callback pour un succès obtenu."""
        player_name = data.get("player_name", "Unknown")
        achievement = data.get("achievement", "Unknown")
        description = data.get("description")

        embed = self._create_achievement_embed(
            player_name, achievement, description=description
        )

        for guild_id in self._configs:
            await self.send_notification(
                guild_id, NotificationType.PLAYER_ACHIEVEMENT, embed
            )

    async def _on_chat_message(self, data: Dict[str, Any]):
        """Callback pour un message du chat."""
        player_name = data.get("player_name", "Unknown")
        message = data.get("message", "")

        embed = self._create_chat_relay_embed(player_name, message)

        for guild_id in self._configs:
            await self.send_notification(
                guild_id, NotificationType.CHAT_RELAY, embed
            )

    async def _on_server_status(self, data: Dict[str, Any]):
        """Callback pour le changement de statut du serveur."""
        status = data.get("status", "unknown")
        uptime = data.get("uptime")
        reason = data.get("reason")

        embed = self._create_server_status_embed(
            status, uptime=uptime, reason=reason
        )

        for guild_id in self._configs:
            await self.send_notification(
                guild_id, NotificationType.SERVER_STATUS, embed
            )

    async def _on_performance_alert(self, data: Dict[str, Any]):
        """Callback pour une alerte de performance."""
        alert_type = data.get("alert_type", "Unknown")
        value = data.get("value", 0)
        threshold = data.get("threshold", 0)

        embed = self._create_performance_alert_embed(
            alert_type, value, threshold
        )

        for guild_id in self._configs:
            await self.send_notification(
                guild_id, NotificationType.PERFORMANCE_ALERT, embed
            )

    # =========================================================================
    # Commandes Slash
    # =========================================================================

    notifications_group = app_commands.Group(
        name="notifications",
        description="Gestion des notifications du serveur Minecraft"
    )

    @notifications_group.command(
        name="configure",
        description="Menu interactif de configuration des notifications"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def notifications_configure(self, interaction: discord.Interaction):
        """Affiche le menu interactif de configuration."""
        embed = discord.Embed(
            title="\U0001f514 Configuration des Notifications",
            description=(
                "Utilisez le menu déroulant ci-dessous pour sélectionner "
                "le type de notification à configurer.\n\n"
                "**Types disponibles:**\n"
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )

        for notif_type in NotificationType:
            emoji = NOTIFICATION_EMOJIS[notif_type]
            desc = NOTIFICATION_DESCRIPTIONS[notif_type]
            embed.description += f"{emoji} **{notif_type.value}** - {desc}\n"

        view = ConfigurationView(self, interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view)

    @notifications_group.command(
        name="enable",
        description="Activer un type de notification"
    )
    @app_commands.describe(
        notification_type="Le type de notification à activer"
    )
    @app_commands.choices(notification_type=NOTIFICATION_TYPE_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def notifications_enable(
        self,
        interaction: discord.Interaction,
        notification_type: str
    ):
        """Active un type de notification."""
        notif_type = NotificationType(notification_type)
        await self.set_notification_enabled(
            interaction.guild_id, notif_type, True
        )

        emoji = NOTIFICATION_EMOJIS[notif_type]
        embed = discord.Embed(
            title=f"{emoji} Notification activée",
            description=f"Les notifications **{notification_type}** sont maintenant **activées**.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        await interaction.response.send_message(embed=embed)

    @notifications_group.command(
        name="disable",
        description="Désactiver un type de notification"
    )
    @app_commands.describe(
        notification_type="Le type de notification à désactiver"
    )
    @app_commands.choices(notification_type=NOTIFICATION_TYPE_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def notifications_disable(
        self,
        interaction: discord.Interaction,
        notification_type: str
    ):
        """Désactive un type de notification."""
        notif_type = NotificationType(notification_type)
        await self.set_notification_enabled(
            interaction.guild_id, notif_type, False
        )

        emoji = NOTIFICATION_EMOJIS[notif_type]
        embed = discord.Embed(
            title=f"{emoji} Notification désactivée",
            description=f"Les notifications **{notification_type}** sont maintenant **désactivées**.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        await interaction.response.send_message(embed=embed)

    @notifications_group.command(
        name="channel",
        description="Définir le channel pour un type de notification"
    )
    @app_commands.describe(
        notification_type="Le type de notification",
        channel="Le channel où envoyer les notifications"
    )
    @app_commands.choices(notification_type=NOTIFICATION_TYPE_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def notifications_channel(
        self,
        interaction: discord.Interaction,
        notification_type: str,
        channel: discord.TextChannel
    ):
        """Définit le channel pour un type de notification."""
        notif_type = NotificationType(notification_type)
        await self.set_notification_channel(
            interaction.guild_id, notif_type, channel.id
        )

        emoji = NOTIFICATION_EMOJIS[notif_type]
        embed = discord.Embed(
            title=f"{emoji} Channel configuré",
            description=(
                f"Les notifications **{notification_type}** seront "
                f"envoyées dans {channel.mention}."
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )

        await interaction.response.send_message(embed=embed)

    @notifications_group.command(
        name="test",
        description="Tester une notification"
    )
    @app_commands.describe(
        notification_type="Le type de notification à tester"
    )
    @app_commands.choices(notification_type=NOTIFICATION_TYPE_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def notifications_test(
        self,
        interaction: discord.Interaction,
        notification_type: str
    ):
        """Envoie une notification de test."""
        notif_type = NotificationType(notification_type)

        await interaction.response.defer()

        success = await self.send_test_notification(
            interaction.guild_id, notif_type
        )

        emoji = NOTIFICATION_EMOJIS[notif_type]

        if success:
            embed = discord.Embed(
                title=f"{emoji} Test envoyé",
                description=f"La notification de test **{notification_type}** a été envoyée!",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
        else:
            embed = discord.Embed(
                title="\u274c Échec du test",
                description=(
                    f"Impossible d'envoyer la notification **{notification_type}**.\n\n"
                    "Vérifiez que:\n"
                    "- La notification est activée\n"
                    "- Un channel est configuré\n"
                    "- Le bot a les permissions d'envoyer des messages"
                ),
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )

        await interaction.followup.send(embed=embed)

    @notifications_group.command(
        name="status",
        description="Afficher le statut de toutes les notifications"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def notifications_status(self, interaction: discord.Interaction):
        """Affiche le statut de toutes les notifications configurées."""
        embed = discord.Embed(
            title="\U0001f514 Statut des Notifications",
            description="Configuration actuelle des notifications:",
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )

        for notif_type in NotificationType:
            config = await self.get_notification_config(
                interaction.guild_id, notif_type
            )

            emoji = NOTIFICATION_EMOJIS[notif_type]
            status_emoji = "\u2705" if config.enabled else "\u274c"

            channel_text = (
                f"<#{config.channel_id}>" if config.channel_id else "Non défini"
            )

            embed.add_field(
                name=f"{emoji} {notif_type.value}",
                value=f"{status_emoji} | {channel_text}",
                inline=True
            )

        await interaction.response.send_message(embed=embed)

    # =========================================================================
    # Gestion des erreurs
    # =========================================================================

    @notifications_configure.error
    @notifications_enable.error
    @notifications_disable.error
    @notifications_channel.error
    @notifications_test.error
    @notifications_status.error
    async def notifications_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        """Gère les erreurs des commandes de notifications."""
        if isinstance(error, app_commands.MissingPermissions):
            embed = discord.Embed(
                title="\u274c Permission refusée",
                description="Vous devez avoir la permission **Gérer le serveur** pour utiliser cette commande.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="\u274c Erreur",
                description=f"Une erreur est survenue: {str(error)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Fonction de setup pour charger le cog."""
    await bot.add_cog(NotificationsCog(bot))
