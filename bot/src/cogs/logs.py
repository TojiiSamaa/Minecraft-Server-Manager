"""
Cog de visualisation et gestion des logs.
Commandes pour afficher, rechercher, filtrer et exporter les logs du bot et du serveur.

Fonctionnalites:
- /logs view, search, stats, export, channel, clear
- /audit view, search
- Pagination avec boutons
- Embeds colores par niveau
- Rate limiting et permissions
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import json
import csv
import io
import re

from ..utils.permissions import PermissionLevel, get_permission_level, require_level, admin_only, moderator_only


# ==================== Constantes et Configuration ====================

class LogLevel(Enum):
    """Niveaux de log disponibles."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogModule(Enum):
    """Modules/categories de logs."""
    SYSTEM = "system"
    DISCORD = "discord"
    MINECRAFT = "minecraft"
    RCON = "rcon"
    DOCKER = "docker"
    DATABASE = "database"
    WEB = "web"
    SECURITY = "security"
    BACKUP = "backup"
    PERFORMANCE = "performance"


class AuditAction(Enum):
    """Types d'actions d'audit."""
    COMMAND_EXECUTE = "command_execute"
    SERVER_START = "server_start"
    SERVER_STOP = "server_stop"
    SERVER_RESTART = "server_restart"
    PLAYER_KICK = "player_kick"
    PLAYER_BAN = "player_ban"
    PLAYER_UNBAN = "player_unban"
    WHITELIST_ADD = "whitelist_add"
    WHITELIST_REMOVE = "whitelist_remove"
    BACKUP_CREATE = "backup_create"
    BACKUP_RESTORE = "backup_restore"
    CONFIG_CHANGE = "config_change"
    PERMISSION_CHANGE = "permission_change"


# Couleurs pour les embeds selon le niveau
LEVEL_COLORS = {
    "DEBUG": 0x808080,      # Gris
    "INFO": 0x3498db,       # Bleu
    "WARNING": 0xf1c40f,    # Jaune
    "ERROR": 0xe74c3c,      # Rouge
    "CRITICAL": 0x8b0000,   # Rouge fonce
}

# Emojis pour les niveaux
LEVEL_EMOJIS = {
    "DEBUG": "[DEBUG]",
    "INFO": "[INFO]",
    "WARNING": "[WARN]",
    "ERROR": "[ERROR]",
    "CRITICAL": "[CRIT]",
}

# Emojis pour les modules
MODULE_EMOJIS = {
    "system": "[SYS]",
    "discord": "[DISC]",
    "minecraft": "[MC]",
    "rcon": "[RCON]",
    "docker": "[DOCKER]",
    "database": "[DB]",
    "web": "[WEB]",
    "security": "[SEC]",
    "backup": "[BACKUP]",
    "performance": "[PERF]",
}


# ==================== Dataclasses ====================

@dataclass
class LogEntry:
    """Represente une entree de log."""
    id: int
    timestamp: datetime
    level: str
    module: str
    message: str
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    guild_id: Optional[int] = None
    player_name: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convertit en dictionnaire."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "module": self.module,
            "message": self.message,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "guild_id": self.guild_id,
            "player_name": self.player_name,
            "context": self.context,
        }


@dataclass
class AuditEntry:
    """Represente une entree d'audit."""
    id: int
    timestamp: datetime
    action: str
    user_id: int
    user_name: str
    guild_id: Optional[int] = None
    target: Optional[str] = None
    details: Optional[str] = None
    success: bool = True

    def to_dict(self) -> dict:
        """Convertit en dictionnaire."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "guild_id": self.guild_id,
            "target": self.target,
            "details": self.details,
            "success": self.success,
        }


# ==================== Views ====================

class LogsPaginationView(discord.ui.View):
    """View avec pagination pour les logs."""

    def __init__(
        self,
        logs: List[LogEntry],
        author_id: int,
        per_page: int = 10,
        title: str = "Logs",
        keyword: Optional[str] = None,
        timeout: float = 180.0
    ):
        super().__init__(timeout=timeout)
        self.logs = logs
        self.author_id = author_id
        self.per_page = per_page
        self.title = title
        self.keyword = keyword
        self.current_page = 0
        self.total_pages = max(1, (len(logs) + per_page - 1) // per_page)
        self.current_level_filter: Optional[str] = None
        self.current_module_filter: Optional[str] = None
        self._update_buttons()

    def _update_buttons(self):
        """Met a jour l'etat des boutons."""
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page >= self.total_pages - 1
        self.last_page.disabled = self.current_page >= self.total_pages - 1

    def get_filtered_logs(self) -> List[LogEntry]:
        """Retourne les logs filtres."""
        filtered = self.logs
        if self.current_level_filter:
            filtered = [log for log in filtered if log.level == self.current_level_filter]
        if self.current_module_filter:
            filtered = [log for log in filtered if log.module == self.current_module_filter]
        return filtered

    def _highlight_keyword(self, text: str) -> str:
        """Met en surbrillance le mot-cle dans le texte."""
        if not self.keyword:
            return text
        pattern = re.compile(re.escape(self.keyword), re.IGNORECASE)
        return pattern.sub(f"**__{self.keyword}__**", text)

    def get_embed(self) -> discord.Embed:
        """Genere l'embed pour la page actuelle."""
        filtered_logs = self.get_filtered_logs()
        self.total_pages = max(1, (len(filtered_logs) + self.per_page - 1) // self.per_page)

        if self.current_page >= self.total_pages:
            self.current_page = max(0, self.total_pages - 1)

        # Determiner la couleur de l'embed
        color = 0x3498db  # Bleu par defaut
        if self.current_level_filter:
            color = LEVEL_COLORS.get(self.current_level_filter, color)

        embed = discord.Embed(
            title=f"[LOGS] {self.title}",
            color=color,
            timestamp=datetime.utcnow()
        )

        if not filtered_logs:
            embed.description = "*Aucun log a afficher.*"
            embed.set_footer(text="Page 0/0")
            return embed

        start = self.current_page * self.per_page
        end = start + self.per_page
        page_logs = filtered_logs[start:end]

        description_lines = []
        for log in page_logs:
            line = self._format_log_entry(log)
            description_lines.append(line)

        embed.description = "\n\n".join(description_lines)

        # Filtres actifs
        filters = []
        if self.current_level_filter:
            filters.append(f"Niveau: {self.current_level_filter}")
        if self.current_module_filter:
            filters.append(f"Module: {self.current_module_filter}")
        if self.keyword:
            filters.append(f"Recherche: '{self.keyword}'")

        if filters:
            embed.add_field(name="Filtres actifs", value=" | ".join(filters), inline=False)

        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages} | Total: {len(filtered_logs)} logs")
        return embed

    def _format_log_entry(self, entry: LogEntry) -> str:
        """Formate une entree de log pour l'affichage."""
        timestamp_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        level_emoji = LEVEL_EMOJIS.get(entry.level, "[LOG]")
        module_emoji = MODULE_EMOJIS.get(entry.module, "[MOD]")

        # Ligne principale
        main_line = f"`{timestamp_str}` {level_emoji} {module_emoji}"

        # Message avec highlight du keyword
        message = entry.message[:200] + ('...' if len(entry.message) > 200 else '')
        message = self._highlight_keyword(message)
        message_line = f"> {message}"

        # Details
        details = []
        if entry.user_name:
            details.append(f"User: **{entry.user_name}**")
        if entry.player_name:
            details.append(f"Player: **{entry.player_name}**")

        result = f"{main_line}\n{message_line}"
        if details:
            result += f"\n> *{' | '.join(details)}*"

        return result

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verifie que seul l'auteur peut interagir."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Vous ne pouvez pas utiliser ces boutons.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="<<", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Premiere page."""
        self.current_page = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Page precedente."""
        self.current_page = max(0, self.current_page - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Page suivante."""
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Derniere page."""
        self.current_page = self.total_pages - 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.success)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rafraichit les logs."""
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.select(
        placeholder="Filtrer par niveau...",
        options=[
            discord.SelectOption(label="Tous les niveaux", value="all"),
            discord.SelectOption(label="DEBUG", value="DEBUG"),
            discord.SelectOption(label="INFO", value="INFO"),
            discord.SelectOption(label="WARNING", value="WARNING"),
            discord.SelectOption(label="ERROR", value="ERROR"),
            discord.SelectOption(label="CRITICAL", value="CRITICAL"),
        ]
    )
    async def level_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Filtre par niveau."""
        value = select.values[0]
        self.current_level_filter = None if value == "all" else value
        self.current_page = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.select(
        placeholder="Filtrer par module...",
        options=[
            discord.SelectOption(label="Tous les modules", value="all"),
            discord.SelectOption(label="System", value="system"),
            discord.SelectOption(label="Discord", value="discord"),
            discord.SelectOption(label="Minecraft", value="minecraft"),
            discord.SelectOption(label="RCON", value="rcon"),
            discord.SelectOption(label="Docker", value="docker"),
            discord.SelectOption(label="Database", value="database"),
            discord.SelectOption(label="Web", value="web"),
            discord.SelectOption(label="Security", value="security"),
            discord.SelectOption(label="Backup", value="backup"),
            discord.SelectOption(label="Performance", value="performance"),
        ]
    )
    async def module_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Filtre par module."""
        value = select.values[0]
        self.current_module_filter = None if value == "all" else value
        self.current_page = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


class AuditPaginationView(discord.ui.View):
    """View avec pagination pour les audits."""

    def __init__(
        self,
        audits: List[AuditEntry],
        author_id: int,
        per_page: int = 10,
        title: str = "Audit Log",
        keyword: Optional[str] = None,
        timeout: float = 180.0
    ):
        super().__init__(timeout=timeout)
        self.audits = audits
        self.author_id = author_id
        self.per_page = per_page
        self.title = title
        self.keyword = keyword
        self.current_page = 0
        self.total_pages = max(1, (len(audits) + per_page - 1) // per_page)
        self._update_buttons()

    def _update_buttons(self):
        """Met a jour l'etat des boutons."""
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page >= self.total_pages - 1
        self.last_page.disabled = self.current_page >= self.total_pages - 1

    def _highlight_keyword(self, text: str) -> str:
        """Met en surbrillance le mot-cle dans le texte."""
        if not self.keyword or not text:
            return text or ""
        pattern = re.compile(re.escape(self.keyword), re.IGNORECASE)
        return pattern.sub(f"**__{self.keyword}__**", text)

    def get_embed(self) -> discord.Embed:
        """Genere l'embed pour la page actuelle."""
        embed = discord.Embed(
            title=f"[AUDIT] {self.title}",
            color=0x9b59b6,  # Violet
            timestamp=datetime.utcnow()
        )

        if not self.audits:
            embed.description = "*Aucune action d'audit a afficher.*"
            embed.set_footer(text="Page 0/0")
            return embed

        start = self.current_page * self.per_page
        end = start + self.per_page
        page_audits = self.audits[start:end]

        description_lines = []
        for audit in page_audits:
            line = self._format_audit_entry(audit)
            description_lines.append(line)

        embed.description = "\n\n".join(description_lines)

        if self.keyword:
            embed.add_field(name="Recherche", value=f"'{self.keyword}'", inline=False)

        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages} | Total: {len(self.audits)} actions")
        return embed

    def _format_audit_entry(self, entry: AuditEntry) -> str:
        """Formate une entree d'audit pour l'affichage."""
        timestamp_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        status = "[OK]" if entry.success else "[FAIL]"

        main_line = f"`{timestamp_str}` {status} **{entry.action}**"

        details = [f"Par: **{entry.user_name}**"]
        if entry.target:
            target = self._highlight_keyword(entry.target)
            details.append(f"Cible: {target}")

        details_line = f"> {' | '.join(details)}"

        result = f"{main_line}\n{details_line}"

        if entry.details:
            detail_text = self._highlight_keyword(entry.details[:100])
            result += f"\n> *{detail_text}*"

        return result

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verifie que seul l'auteur peut interagir."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Vous ne pouvez pas utiliser ces boutons.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="<<", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.total_pages - 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


class LogStatsView(discord.ui.View):
    """View pour les statistiques de logs."""

    def __init__(self, cog: 'LogsCog', author_id: int, period: str = "day"):
        super().__init__(timeout=120.0)
        self.cog = cog
        self.author_id = author_id
        self.period = period

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Vous ne pouvez pas utiliser ces boutons.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="24h", style=discord.ButtonStyle.primary)
    async def day_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.period = "day"
        embed = await self.cog.create_stats_embed(self.period)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="7 jours", style=discord.ButtonStyle.primary)
    async def week_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.period = "week"
        embed = await self.cog.create_stats_embed(self.period)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="30 jours", style=discord.ButtonStyle.primary)
    async def month_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.period = "month"
        embed = await self.cog.create_stats_embed(self.period)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Actualiser", style=discord.ButtonStyle.success)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.cog.create_stats_embed(self.period)
        await interaction.response.edit_message(embed=embed, view=self)


class ConfirmExportView(discord.ui.View):
    """View de confirmation pour l'export."""

    def __init__(self, author_id: int):
        super().__init__(timeout=30.0)
        self.author_id = author_id
        self.value: Optional[bool] = None
        self.send_dm: bool = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Vous ne pouvez pas utiliser ces boutons.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Envoyer ici", style=discord.ButtonStyle.primary)
    async def send_here(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.send_dm = False
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Envoyer en DM", style=discord.ButtonStyle.secondary)
    async def send_dm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.send_dm = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.defer()


class ConfirmClearView(discord.ui.View):
    """View de confirmation pour la suppression des logs."""

    def __init__(self, author_id: int, before_date: str, log_count: int):
        super().__init__(timeout=30.0)
        self.author_id = author_id
        self.before_date = before_date
        self.log_count = log_count
        self.value: Optional[bool] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Vous ne pouvez pas utiliser ces boutons.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Confirmer la suppression", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.defer()


# ==================== Fonctions utilitaires ====================

def create_ascii_bar(percentage: float, width: int = 20) -> str:
    """Cree une barre ASCII pour les statistiques."""
    filled = int(percentage / 100 * width)
    empty = width - filled
    return f"[{'=' * filled}{' ' * empty}] {percentage:.1f}%"


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse une date depuis une chaine YYYY-MM-DD."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


# ==================== Rate Limiter ====================

class RateLimiter:
    """Rate limiter simple pour les commandes."""

    def __init__(self, rate: int, per: float):
        """
        Args:
            rate: Nombre d'appels autorises
            per: Periode en secondes
        """
        self.rate = rate
        self.per = per
        self._cache: Dict[int, List[float]] = {}

    def is_rate_limited(self, user_id: int) -> bool:
        """Verifie si l'utilisateur est rate limited."""
        now = datetime.utcnow().timestamp()

        if user_id not in self._cache:
            self._cache[user_id] = []

        # Nettoyer les anciennes entrees
        self._cache[user_id] = [
            ts for ts in self._cache[user_id]
            if now - ts < self.per
        ]

        if len(self._cache[user_id]) >= self.rate:
            return True

        self._cache[user_id].append(now)
        return False

    def get_retry_after(self, user_id: int) -> float:
        """Retourne le temps restant avant de pouvoir reessayer."""
        if user_id not in self._cache or not self._cache[user_id]:
            return 0.0

        now = datetime.utcnow().timestamp()
        oldest = min(self._cache[user_id])
        return max(0.0, self.per - (now - oldest))


# ==================== Cog Principal ====================

class LogsCog(commands.Cog):
    """Cog pour la visualisation et gestion des logs."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Stockage en memoire des logs
        self._logs: List[LogEntry] = []
        self._log_id_counter = 0

        # Stockage des audits
        self._audits: List[AuditEntry] = []
        self._audit_id_counter = 0

        # Configuration des channels par niveau de log
        self._level_channels: Dict[str, int] = {}

        # Rate limiter: 5 commandes par 30 secondes
        self._rate_limiter = RateLimiter(rate=5, per=30.0)

        # Demarrer la tache de nettoyage
        self.cleanup_old_logs.start()

    async def cog_unload(self):
        """Arrete les taches de fond."""
        self.cleanup_old_logs.cancel()

    @tasks.loop(hours=24)
    async def cleanup_old_logs(self):
        """Nettoie les logs de plus de 30 jours."""
        cutoff = datetime.utcnow() - timedelta(days=30)
        self._logs = [log for log in self._logs if log.timestamp > cutoff]
        self._audits = [audit for audit in self._audits if audit.timestamp > cutoff]

    @cleanup_old_logs.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

    # ==================== Methodes internes ====================

    def _check_rate_limit(self, interaction: discord.Interaction) -> Optional[str]:
        """Verifie le rate limit et retourne un message d'erreur si limite."""
        if self._rate_limiter.is_rate_limited(interaction.user.id):
            retry_after = self._rate_limiter.get_retry_after(interaction.user.id)
            return f"Rate limit atteint. Reessayez dans {retry_after:.1f} secondes."
        return None

    def _is_owner(self, interaction: discord.Interaction) -> bool:
        """Verifie si l'utilisateur est owner du bot."""
        return interaction.user.id in getattr(self.bot, 'owner_ids', [])

    async def add_log(
        self,
        level: str,
        module: str,
        message: str,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        guild_id: Optional[int] = None,
        player_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> LogEntry:
        """Ajoute une entree de log."""
        self._log_id_counter += 1
        entry = LogEntry(
            id=self._log_id_counter,
            timestamp=datetime.utcnow(),
            level=level.upper(),
            module=module.lower(),
            message=message,
            user_id=user_id,
            user_name=user_name,
            guild_id=guild_id,
            player_name=player_name,
            context=context or {}
        )
        self._logs.append(entry)

        # Envoyer au channel configure pour ce niveau
        await self._send_to_level_channel(entry)

        return entry

    async def add_audit(
        self,
        action: str,
        user_id: int,
        user_name: str,
        guild_id: Optional[int] = None,
        target: Optional[str] = None,
        details: Optional[str] = None,
        success: bool = True
    ) -> AuditEntry:
        """Ajoute une entree d'audit."""
        self._audit_id_counter += 1
        entry = AuditEntry(
            id=self._audit_id_counter,
            timestamp=datetime.utcnow(),
            action=action,
            user_id=user_id,
            user_name=user_name,
            guild_id=guild_id,
            target=target,
            details=details,
            success=success
        )
        self._audits.append(entry)
        return entry

    async def _send_to_level_channel(self, entry: LogEntry):
        """Envoie un log au channel Discord configure pour ce niveau."""
        channel_id = self._level_channels.get(entry.level)
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        try:
            embed = discord.Embed(
                title=f"{LEVEL_EMOJIS.get(entry.level, '[LOG]')} {entry.level}",
                description=f"**Module:** {entry.module}\n\n{entry.message[:4000]}",
                color=LEVEL_COLORS.get(entry.level, 0x3498db),
                timestamp=entry.timestamp
            )

            if entry.user_name:
                embed.add_field(name="Utilisateur", value=entry.user_name, inline=True)
            if entry.player_name:
                embed.add_field(name="Joueur", value=entry.player_name, inline=True)

            await channel.send(embed=embed)
        except discord.Forbidden:
            pass
        except Exception:
            pass

    async def get_logs(
        self,
        level: Optional[str] = None,
        module: Optional[str] = None,
        user_id: Optional[int] = None,
        player_name: Optional[str] = None,
        keyword: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[LogEntry]:
        """Recupere les logs avec filtres."""
        result = self._logs.copy()

        if level:
            result = [log for log in result if log.level == level.upper()]
        if module:
            result = [log for log in result if log.module == module.lower()]
        if user_id:
            result = [log for log in result if log.user_id == user_id]
        if player_name:
            result = [log for log in result if log.player_name and player_name.lower() in log.player_name.lower()]
        if keyword:
            keyword_lower = keyword.lower()
            result = [log for log in result if keyword_lower in log.message.lower()]
        if start_date:
            result = [log for log in result if log.timestamp >= start_date]
        if end_date:
            result = [log for log in result if log.timestamp <= end_date]

        result.sort(key=lambda log: log.timestamp, reverse=True)
        return result[:limit]

    async def get_audits(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """Recupere les audits avec filtres."""
        result = self._audits.copy()

        if user_id:
            result = [audit for audit in result if audit.user_id == user_id]
        if action:
            result = [audit for audit in result if audit.action == action]
        if keyword:
            keyword_lower = keyword.lower()
            result = [
                audit for audit in result
                if (keyword_lower in (audit.target or "").lower() or
                    keyword_lower in (audit.details or "").lower() or
                    keyword_lower in audit.action.lower())
            ]

        result.sort(key=lambda audit: audit.timestamp, reverse=True)
        return result[:limit]

    async def get_stats(self, period: str = "day") -> Dict[str, Any]:
        """Calcule les statistiques des logs."""
        now = datetime.utcnow()
        if period == "day":
            start = now - timedelta(days=1)
        elif period == "week":
            start = now - timedelta(weeks=1)
        else:
            start = now - timedelta(days=30)

        logs = [log for log in self._logs if log.timestamp >= start]

        # Compter par niveau
        level_counts = {}
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            level_counts[level] = len([log for log in logs if log.level == level])

        # Compter par module
        module_counts = {}
        for mod in LogModule:
            module_counts[mod.value] = len([log for log in logs if log.module == mod.value])

        # Top 5 modules avec erreurs
        error_modules = {}
        for log in logs:
            if log.level in ["ERROR", "CRITICAL"]:
                error_modules[log.module] = error_modules.get(log.module, 0) + 1

        top_error_modules = sorted(error_modules.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total": len(logs),
            "period": period,
            "start": start,
            "end": now,
            "by_level": level_counts,
            "by_module": module_counts,
            "top_error_modules": top_error_modules,
        }

    async def create_stats_embed(self, period: str = "day") -> discord.Embed:
        """Cree un embed avec les statistiques."""
        stats = await self.get_stats(period)

        period_names = {"day": "24 heures", "week": "7 jours", "month": "30 jours"}
        period_name = period_names.get(period, period)

        embed = discord.Embed(
            title=f"[STATS] Statistiques des Logs - {period_name}",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )

        total = stats["total"]
        embed.add_field(
            name="Total",
            value=f"**{total}** logs",
            inline=False
        )

        # Statistiques par niveau avec barres ASCII
        level_lines = []
        for level, count in stats["by_level"].items():
            percentage = (count / total * 100) if total > 0 else 0
            emoji = LEVEL_EMOJIS.get(level, "[LOG]")
            bar = create_ascii_bar(percentage, 15)
            level_lines.append(f"{emoji} **{level}**: {count} {bar}")

        embed.add_field(
            name="Par niveau",
            value="\n".join(level_lines) if level_lines else "*Aucune donnee*",
            inline=False
        )

        # Top 5 modules avec erreurs
        if stats["top_error_modules"]:
            error_lines = []
            for module, count in stats["top_error_modules"]:
                emoji = MODULE_EMOJIS.get(module, "[MOD]")
                error_lines.append(f"{emoji} **{module}**: {count} erreurs")

            embed.add_field(
                name="Top 5 modules avec erreurs",
                value="\n".join(error_lines),
                inline=False
            )

        embed.set_footer(
            text=f"Periode: {stats['start'].strftime('%Y-%m-%d %H:%M')} - {stats['end'].strftime('%Y-%m-%d %H:%M')}"
        )

        return embed

    async def export_logs(
        self,
        logs: List[LogEntry],
        format: str = "json"
    ) -> tuple[str, io.BytesIO]:
        """Exporte les logs dans le format specifie."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if format == "json":
            filename = f"logs_{timestamp}.json"
            data = json.dumps([log.to_dict() for log in logs], indent=2, ensure_ascii=False)
            buffer = io.BytesIO(data.encode('utf-8'))

        elif format == "csv":
            filename = f"logs_{timestamp}.csv"
            buffer = io.BytesIO()
            text_buffer = io.StringIO()

            writer = csv.writer(text_buffer)
            writer.writerow([
                "ID", "Timestamp", "Level", "Module", "Message",
                "User ID", "User Name", "Guild ID", "Player Name", "Context"
            ])

            for log in logs:
                writer.writerow([
                    log.id,
                    log.timestamp.isoformat(),
                    log.level,
                    log.module,
                    log.message,
                    log.user_id or "",
                    log.user_name or "",
                    log.guild_id or "",
                    log.player_name or "",
                    json.dumps(log.context) if log.context else ""
                ])

            buffer.write(text_buffer.getvalue().encode('utf-8'))
            buffer.seek(0)

        else:  # txt
            filename = f"logs_{timestamp}.txt"
            lines = []
            for log in logs:
                line = (
                    f"[{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"[{log.level}] [{log.module}] {log.message}"
                )
                if log.user_name:
                    line += f" | User: {log.user_name}"
                if log.player_name:
                    line += f" | Player: {log.player_name}"
                lines.append(line)

            buffer = io.BytesIO("\n".join(lines).encode('utf-8'))

        buffer.seek(0)
        return filename, buffer

    # ==================== Autocomplete ====================

    async def level_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete pour les niveaux de log."""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        return [
            app_commands.Choice(name=level, value=level)
            for level in levels
            if current.upper() in level
        ][:25]

    async def module_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete pour les modules."""
        modules = [mod.value for mod in LogModule]
        return [
            app_commands.Choice(name=mod, value=mod)
            for mod in modules
            if current.lower() in mod.lower()
        ][:25]

    async def action_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete pour les actions d'audit."""
        actions = [action.value for action in AuditAction]
        return [
            app_commands.Choice(name=action.replace("_", " ").title(), value=action)
            for action in actions
            if current.lower() in action.lower()
        ][:25]

    async def format_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete pour les formats d'export."""
        formats = [
            ("json", "JSON - Structure complete"),
            ("csv", "CSV - Tableur"),
            ("txt", "TXT - Texte brut"),
        ]
        return [
            app_commands.Choice(name=f"{fmt} ({desc})", value=fmt)
            for fmt, desc in formats
            if current.lower() in fmt.lower() or current.lower() in desc.lower()
        ][:25]

    # ==================== Groupe de commandes /logs ====================

    logs_group = app_commands.Group(name="logs", description="Visualisation et gestion des logs")

    @logs_group.command(name="view", description="Affiche les derniers logs")
    @app_commands.describe(
        level="Filtrer par niveau de log",
        module="Filtrer par module",
        limit="Nombre de logs a afficher (defaut: 50, max: 200)"
    )
    @app_commands.autocomplete(level=level_autocomplete, module=module_autocomplete)
    @moderator_only()
    async def logs_view(
        self,
        interaction: discord.Interaction,
        level: Optional[str] = None,
        module: Optional[str] = None,
        limit: Optional[app_commands.Range[int, 1, 200]] = 50
    ):
        """Affiche les derniers logs avec filtres optionnels."""
        # Rate limit check
        rate_error = self._check_rate_limit(interaction)
        if rate_error:
            await interaction.response.send_message(rate_error, ephemeral=True)
            return

        await interaction.response.defer()

        logs = await self.get_logs(level=level, module=module, limit=limit)

        if not logs:
            embed = discord.Embed(
                title="[LOGS] Logs",
                description="*Aucun log trouve avec ces filtres.*",
                color=0x808080,
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=embed)
            return

        view = LogsPaginationView(logs, interaction.user.id, title="Logs recents")
        if level:
            view.current_level_filter = level.upper()
        if module:
            view.current_module_filter = module.lower()

        embed = view.get_embed()
        await interaction.followup.send(embed=embed, view=view)

        # Logger l'action
        await self.add_audit(
            "command_execute",
            interaction.user.id,
            str(interaction.user),
            guild_id=interaction.guild_id,
            target="/logs view",
            details=f"level={level}, module={module}, limit={limit}"
        )

    @logs_group.command(name="search", description="Recherche dans les logs")
    @app_commands.describe(
        keyword="Mot-cle a rechercher",
        level="Filtrer par niveau de log",
        start_date="Date de debut (format: YYYY-MM-DD)",
        end_date="Date de fin (format: YYYY-MM-DD)"
    )
    @app_commands.autocomplete(level=level_autocomplete)
    @moderator_only()
    async def logs_search(
        self,
        interaction: discord.Interaction,
        keyword: str,
        level: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ):
        """Recherche dans les logs par mot-cle et dates."""
        rate_error = self._check_rate_limit(interaction)
        if rate_error:
            await interaction.response.send_message(rate_error, ephemeral=True)
            return

        await interaction.response.defer()

        # Parser les dates
        start_dt = None
        end_dt = None

        if start_date:
            start_dt = parse_date(start_date)
            if not start_dt:
                await interaction.followup.send(
                    "Format de date invalide pour start_date. Utilisez YYYY-MM-DD.",
                    ephemeral=True
                )
                return

        if end_date:
            end_dt = parse_date(end_date)
            if not end_dt:
                await interaction.followup.send(
                    "Format de date invalide pour end_date. Utilisez YYYY-MM-DD.",
                    ephemeral=True
                )
                return
            end_dt = end_dt.replace(hour=23, minute=59, second=59)

        logs = await self.get_logs(
            keyword=keyword,
            level=level,
            start_date=start_dt,
            end_date=end_dt,
            limit=200
        )

        if not logs:
            embed = discord.Embed(
                title=f"[LOGS] Recherche: '{keyword}'",
                description="*Aucun resultat trouve.*",
                color=0x808080,
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=embed)
            return

        view = LogsPaginationView(
            logs,
            interaction.user.id,
            title=f"Recherche: '{keyword}'",
            keyword=keyword
        )
        if level:
            view.current_level_filter = level.upper()

        embed = view.get_embed()
        await interaction.followup.send(embed=embed, view=view)

    @logs_group.command(name="stats", description="Statistiques des logs")
    @app_commands.describe(period="Periode des statistiques")
    @app_commands.choices(period=[
        app_commands.Choice(name="Dernieres 24 heures", value="day"),
        app_commands.Choice(name="Derniere semaine", value="week"),
        app_commands.Choice(name="Dernier mois", value="month"),
    ])
    @moderator_only()
    async def logs_stats(
        self,
        interaction: discord.Interaction,
        period: Optional[str] = "day"
    ):
        """Affiche les statistiques des logs."""
        rate_error = self._check_rate_limit(interaction)
        if rate_error:
            await interaction.response.send_message(rate_error, ephemeral=True)
            return

        await interaction.response.defer()

        embed = await self.create_stats_embed(period)
        view = LogStatsView(self, interaction.user.id, period)
        await interaction.followup.send(embed=embed, view=view)

    @logs_group.command(name="export", description="Exporte les logs")
    @app_commands.describe(
        format="Format d'export",
        level="Filtrer par niveau de log",
        start_date="Date de debut (format: YYYY-MM-DD)",
        end_date="Date de fin (format: YYYY-MM-DD)"
    )
    @app_commands.autocomplete(format=format_autocomplete, level=level_autocomplete)
    @admin_only()
    async def logs_export(
        self,
        interaction: discord.Interaction,
        format: Optional[str] = "json",
        level: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ):
        """Exporte les logs dans un fichier."""
        rate_error = self._check_rate_limit(interaction)
        if rate_error:
            await interaction.response.send_message(rate_error, ephemeral=True)
            return

        # Valider le format
        if format not in ["json", "csv", "txt"]:
            format = "json"

        # Parser les dates
        start_dt = None
        end_dt = None

        if start_date:
            start_dt = parse_date(start_date)
            if not start_dt:
                await interaction.response.send_message(
                    "Format de date invalide pour start_date. Utilisez YYYY-MM-DD.",
                    ephemeral=True
                )
                return

        if end_date:
            end_dt = parse_date(end_date)
            if not end_dt:
                await interaction.response.send_message(
                    "Format de date invalide pour end_date. Utilisez YYYY-MM-DD.",
                    ephemeral=True
                )
                return
            end_dt = end_dt.replace(hour=23, minute=59, second=59)

        # Demander confirmation
        embed = discord.Embed(
            title="[EXPORT] Export des logs",
            description=(
                f"**Periode:** {start_date or 'Debut'} - {end_date or 'Maintenant'}\n"
                f"**Format:** {format.upper()}\n"
                f"**Niveau:** {level or 'Tous'}\n\n"
                "Ou souhaitez-vous recevoir le fichier ?"
            ),
            color=0x3498db
        )

        view = ConfirmExportView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)

        await view.wait()

        if view.value is None:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="[EXPORT] Annule",
                    description="La demande a expire.",
                    color=0x808080
                ),
                view=None
            )
            return

        if not view.value:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="[EXPORT] Annule",
                    description="L'export a ete annule.",
                    color=0xe74c3c
                ),
                view=None
            )
            return

        # Recuperer les logs (max 10000)
        logs = await self.get_logs(
            level=level,
            start_date=start_dt,
            end_date=end_dt,
            limit=10000
        )

        if not logs:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="[EXPORT] Aucun log",
                    description="Aucun log trouve pour ces criteres.",
                    color=0xe74c3c
                ),
                view=None
            )
            return

        # Exporter
        filename, buffer = await self.export_logs(logs, format)
        file = discord.File(buffer, filename=filename)

        try:
            if view.send_dm:
                await interaction.user.send(
                    f"Voici l'export des logs ({len(logs)} entrees):",
                    file=file
                )
                await interaction.edit_original_response(
                    embed=discord.Embed(
                        title="[EXPORT] Envoye",
                        description=f"L'export a ete envoye en DM.\n**Fichier:** {filename}\n**Logs:** {len(logs)}",
                        color=0x2ecc71
                    ),
                    view=None
                )
            else:
                await interaction.edit_original_response(
                    embed=discord.Embed(
                        title="[EXPORT] Termine",
                        description=f"**Fichier:** {filename}\n**Logs:** {len(logs)}",
                        color=0x2ecc71
                    ),
                    view=None
                )
                await interaction.followup.send(file=file)

        except discord.Forbidden:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="[EXPORT] Erreur",
                    description="Impossible d'envoyer le fichier. Verifiez vos DMs.",
                    color=0xe74c3c
                ),
                view=None
            )

        # Logger l'export
        await self.add_audit(
            "command_execute",
            interaction.user.id,
            str(interaction.user),
            guild_id=interaction.guild_id,
            target="/logs export",
            details=f"format={format}, logs={len(logs)}"
        )

    @logs_group.command(name="channel", description="Configure le channel de destination pour un niveau de log")
    @app_commands.describe(
        level="Niveau de log",
        channel="Channel de destination"
    )
    @app_commands.choices(level=[
        app_commands.Choice(name="DEBUG", value="DEBUG"),
        app_commands.Choice(name="INFO", value="INFO"),
        app_commands.Choice(name="WARNING", value="WARNING"),
        app_commands.Choice(name="ERROR", value="ERROR"),
        app_commands.Choice(name="CRITICAL", value="CRITICAL"),
    ])
    @admin_only()
    async def logs_channel(
        self,
        interaction: discord.Interaction,
        level: str,
        channel: discord.TextChannel
    ):
        """Configure le channel pour un niveau de log specifique."""
        self._level_channels[level.upper()] = channel.id

        embed = discord.Embed(
            title="[CONFIG] Channel configure",
            description=(
                f"Les logs de niveau **{level}** seront envoyes dans {channel.mention}."
            ),
            color=LEVEL_COLORS.get(level.upper(), 0x3498db),
            timestamp=datetime.utcnow()
        )

        await interaction.response.send_message(embed=embed)

        await self.add_audit(
            "config_change",
            interaction.user.id,
            str(interaction.user),
            guild_id=interaction.guild_id,
            target=f"logs_channel_{level}",
            details=f"channel_id={channel.id}"
        )

    @logs_group.command(name="clear", description="Supprime les logs avant une date")
    @app_commands.describe(
        before_date="Date limite (format: YYYY-MM-DD). Les logs avant cette date seront supprimes."
    )
    async def logs_clear(
        self,
        interaction: discord.Interaction,
        before_date: str
    ):
        """Supprime les logs avant une date (Owner uniquement)."""
        # Verifier si owner
        if not self._is_owner(interaction):
            await interaction.response.send_message(
                "Cette commande est reservee aux owners du bot.",
                ephemeral=True
            )
            return

        # Parser la date
        before_dt = parse_date(before_date)
        if not before_dt:
            await interaction.response.send_message(
                "Format de date invalide. Utilisez YYYY-MM-DD.",
                ephemeral=True
            )
            return

        # Compter les logs a supprimer
        logs_to_delete = [log for log in self._logs if log.timestamp < before_dt]
        count = len(logs_to_delete)

        if count == 0:
            await interaction.response.send_message(
                f"Aucun log trouve avant le {before_date}.",
                ephemeral=True
            )
            return

        # Demander confirmation
        embed = discord.Embed(
            title="[CLEAR] Confirmation requise",
            description=(
                f"**{count}** logs seront supprimes definitivement.\n\n"
                f"Date limite: **{before_date}**\n\n"
                "Cette action est irreversible."
            ),
            color=0xe74c3c,
            timestamp=datetime.utcnow()
        )

        view = ConfirmClearView(interaction.user.id, before_date, count)
        await interaction.response.send_message(embed=embed, view=view)

        await view.wait()

        if view.value is None:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="[CLEAR] Annule",
                    description="La demande a expire.",
                    color=0x808080
                ),
                view=None
            )
            return

        if not view.value:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="[CLEAR] Annule",
                    description="La suppression a ete annulee.",
                    color=0x808080
                ),
                view=None
            )
            return

        # Supprimer les logs
        self._logs = [log for log in self._logs if log.timestamp >= before_dt]

        await interaction.edit_original_response(
            embed=discord.Embed(
                title="[CLEAR] Suppression terminee",
                description=f"**{count}** logs ont ete supprimes.",
                color=0x2ecc71,
                timestamp=datetime.utcnow()
            ),
            view=None
        )

        await self.add_audit(
            "command_execute",
            interaction.user.id,
            str(interaction.user),
            guild_id=interaction.guild_id,
            target="/logs clear",
            details=f"before_date={before_date}, deleted={count}"
        )

    # ==================== Groupe de commandes /audit ====================

    audit_group = app_commands.Group(name="audit", description="Visualisation des logs d'audit")

    @audit_group.command(name="view", description="Voir les actions d'audit")
    @app_commands.describe(
        user="Filtrer par utilisateur",
        action="Filtrer par type d'action",
        limit="Nombre d'entrees a afficher (defaut: 50, max: 200)"
    )
    @app_commands.autocomplete(action=action_autocomplete)
    @moderator_only()
    async def audit_view(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
        action: Optional[str] = None,
        limit: Optional[app_commands.Range[int, 1, 200]] = 50
    ):
        """Voir les actions d'audit."""
        rate_error = self._check_rate_limit(interaction)
        if rate_error:
            await interaction.response.send_message(rate_error, ephemeral=True)
            return

        await interaction.response.defer()

        audits = await self.get_audits(
            user_id=user.id if user else None,
            action=action,
            limit=limit
        )

        if not audits:
            embed = discord.Embed(
                title="[AUDIT] Audit Log",
                description="*Aucune action d'audit trouvee.*",
                color=0x808080,
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=embed)
            return

        title = "Audit Log"
        if user:
            title += f" - {user.display_name}"
        if action:
            title += f" - {action}"

        view = AuditPaginationView(audits, interaction.user.id, title=title)
        embed = view.get_embed()
        await interaction.followup.send(embed=embed, view=view)

    @audit_group.command(name="search", description="Recherche dans les logs d'audit")
    @app_commands.describe(
        keyword="Mot-cle a rechercher"
    )
    @moderator_only()
    async def audit_search(
        self,
        interaction: discord.Interaction,
        keyword: str
    ):
        """Recherche dans les logs d'audit."""
        rate_error = self._check_rate_limit(interaction)
        if rate_error:
            await interaction.response.send_message(rate_error, ephemeral=True)
            return

        await interaction.response.defer()

        audits = await self.get_audits(keyword=keyword, limit=200)

        if not audits:
            embed = discord.Embed(
                title=f"[AUDIT] Recherche: '{keyword}'",
                description="*Aucun resultat trouve.*",
                color=0x808080,
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=embed)
            return

        view = AuditPaginationView(
            audits,
            interaction.user.id,
            title=f"Recherche: '{keyword}'",
            keyword=keyword
        )
        embed = view.get_embed()
        await interaction.followup.send(embed=embed, view=view)

    # ==================== Methodes publiques pour autres cogs ====================

    async def log(
        self,
        level: str,
        module: str,
        message: str,
        **kwargs
    ) -> LogEntry:
        """
        Methode publique pour ajouter des logs depuis d'autres cogs.

        Usage:
            logs_cog = bot.get_cog("LogsCog")
            if logs_cog:
                await logs_cog.log("INFO", "minecraft", "Player joined", player_name="Steve")
        """
        return await self.add_log(level, module, message, **kwargs)

    async def audit(
        self,
        action: str,
        user_id: int,
        user_name: str,
        **kwargs
    ) -> AuditEntry:
        """
        Methode publique pour ajouter des audits depuis d'autres cogs.

        Usage:
            logs_cog = bot.get_cog("LogsCog")
            if logs_cog:
                await logs_cog.audit("server_start", user.id, str(user), success=True)
        """
        return await self.add_audit(action, user_id, user_name, **kwargs)


async def setup(bot: commands.Bot):
    """Charge le cog."""
    await bot.add_cog(LogsCog(bot))
