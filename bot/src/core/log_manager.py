"""
Systeme de logs complet pour le bot Discord Minecraft.

Ce module gere les logs sur 3 canaux:
1. Fichiers - logs/YYYY/MM/bot-YYYY-MM-DD.log (rotation quotidienne)
2. Base de donnees - Table logs.bot_logs avec batch insert
3. Discord - Channels configurables par niveau avec rate limiting

Fonctionnalites:
- Compression automatique des vieux logs (gzip apres 7 jours)
- Retention configurable (defaut: 90 jours)
- Batch insert pour performance (buffer 100 logs ou 5 secondes)
- Rate limiting Discord (max 5 messages/seconde)
- Recherche et export de logs
- Statistiques detaillees

Auteur: MinecraftBot
"""

import asyncio
import gzip
import io
import json
import logging
import os
import shutil
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

import aiofiles
import discord

# Logger standard pour ce module
logger = logging.getLogger(__name__)


# =============================================================================
# ENUMERATIONS
# =============================================================================

class LogLevel(Enum):
    """Niveaux de log disponibles avec valeurs numeriques."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    def __str__(self) -> str:
        return self.name

    def __lt__(self, other: "LogLevel") -> bool:
        if isinstance(other, LogLevel):
            return self.value < other.value
        return NotImplemented

    def __le__(self, other: "LogLevel") -> bool:
        if isinstance(other, LogLevel):
            return self.value <= other.value
        return NotImplemented

    def __gt__(self, other: "LogLevel") -> bool:
        if isinstance(other, LogLevel):
            return self.value > other.value
        return NotImplemented

    def __ge__(self, other: "LogLevel") -> bool:
        if isinstance(other, LogLevel):
            return self.value >= other.value
        return NotImplemented

    @classmethod
    def from_string(cls, level_str: str) -> "LogLevel":
        """Convertit une chaine en LogLevel."""
        level_str = level_str.upper().strip()
        for level in cls:
            if level.name == level_str:
                return level
        return cls.INFO

    @classmethod
    def from_value(cls, value: int) -> "LogLevel":
        """Convertit une valeur numerique en LogLevel."""
        for level in cls:
            if level.value == value:
                return level
        return cls.INFO

    @property
    def color(self) -> int:
        """Retourne la couleur Discord associee au niveau."""
        colors = {
            LogLevel.DEBUG: 0x808080,     # Gris
            LogLevel.INFO: 0x3498DB,      # Bleu
            LogLevel.WARNING: 0xF1C40F,   # Jaune/Orange
            LogLevel.ERROR: 0xE74C3C,     # Rouge
            LogLevel.CRITICAL: 0x8B0000,  # Rouge fonce
        }
        return colors.get(self, 0x808080)

    @property
    def emoji(self) -> str:
        """Retourne l'emoji/indicateur associe au niveau."""
        emojis = {
            LogLevel.DEBUG: "[DEBUG]",
            LogLevel.INFO: "[INFO]",
            LogLevel.WARNING: "[WARN]",
            LogLevel.ERROR: "[ERROR]",
            LogLevel.CRITICAL: "[CRIT]",
        }
        return emojis.get(self, "[LOG]")


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class LogEntry:
    """
    Represente une entree de log complete.

    Attributes:
        id: Identifiant unique (optionnel, assigne par la DB)
        timestamp: Date et heure de l'entree
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        module: Module source du log
        message: Message du log
        guild_id: ID du serveur Discord (optionnel)
        user_id: ID de l'utilisateur Discord (optionnel)
        channel_id: ID du channel Discord (optionnel)
        extra_data: Donnees additionnelles en dictionnaire (JSONB)
    """
    timestamp: datetime
    level: LogLevel
    module: str
    message: str
    id: Optional[int] = None
    guild_id: Optional[int] = None
    user_id: Optional[int] = None
    channel_id: Optional[int] = None
    extra_data: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'entree en dictionnaire serialisable."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "module": self.module,
            "message": self.message,
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "extra_data": self.extra_data or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogEntry":
        """Cree une entree depuis un dictionnaire."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        return cls(
            id=data.get("id"),
            timestamp=timestamp,
            level=LogLevel.from_string(data.get("level", "INFO")),
            module=data.get("module", "unknown"),
            message=data.get("message", ""),
            guild_id=data.get("guild_id"),
            user_id=data.get("user_id"),
            channel_id=data.get("channel_id"),
            extra_data=data.get("extra_data", {}),
        )

    @classmethod
    def from_db_row(cls, row: tuple) -> "LogEntry":
        """Cree une entree depuis une ligne de base de donnees."""
        # Format attendu: (id, timestamp, level, module, message, extra_data, guild_id, user_id, channel_id)
        return cls(
            id=row[0],
            timestamp=row[1] if isinstance(row[1], datetime) else datetime.fromisoformat(str(row[1])),
            level=LogLevel.from_string(row[2]),
            module=row[3],
            message=row[4],
            extra_data=json.loads(row[5]) if row[5] and isinstance(row[5], str) else row[5],
            guild_id=row[6] if len(row) > 6 else None,
            user_id=row[7] if len(row) > 7 else None,
            channel_id=row[8] if len(row) > 8 else None,
        )

    def format_file(self) -> str:
        """
        Formate l'entree pour ecriture dans un fichier.
        Format: [YYYY-MM-DD HH:mm:ss.fff] [LEVEL] [module] message
        """
        # Format timestamp avec millisecondes
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M:%S.") + f"{self.timestamp.microsecond // 1000:03d}"

        parts = [
            f"[{ts}]",
            f"[{self.level.name:8}]",
            f"[{self.module}]",
            self.message,
        ]

        # Ajouter les metadonnees si presentes
        meta = []
        if self.guild_id:
            meta.append(f"guild={self.guild_id}")
        if self.user_id:
            meta.append(f"user={self.user_id}")
        if self.channel_id:
            meta.append(f"channel={self.channel_id}")
        if self.extra_data:
            meta.append(f"extra={json.dumps(self.extra_data, ensure_ascii=False)}")

        if meta:
            parts.append(f"| {' '.join(meta)}")

        return " ".join(parts)

    def to_embed(self) -> discord.Embed:
        """Cree un embed Discord pour cette entree."""
        embed = discord.Embed(
            title=f"{self.level.emoji} {self.module.upper()}",
            description=self.message[:4000] if len(self.message) > 4000 else self.message,
            color=self.level.color,
            timestamp=self.timestamp,
        )

        if self.user_id:
            embed.add_field(name="Utilisateur", value=f"<@{self.user_id}>", inline=True)
        if self.guild_id:
            embed.add_field(name="Serveur", value=str(self.guild_id), inline=True)
        if self.channel_id:
            embed.add_field(name="Channel", value=f"<#{self.channel_id}>", inline=True)

        if self.extra_data:
            extra_str = json.dumps(self.extra_data, indent=2, ensure_ascii=False)
            if len(extra_str) > 1000:
                extra_str = extra_str[:997] + "..."
            embed.add_field(name="Donnees", value=f"```json\n{extra_str}\n```", inline=False)

        embed.set_footer(text=f"Log ID: {self.id or 'N/A'}")
        return embed


# =============================================================================
# RATE LIMITER POUR DISCORD
# =============================================================================

class RateLimiter:
    """
    Rate limiter pour controler le debit de messages Discord.
    Limite par defaut: 5 messages par seconde.
    """

    def __init__(self, max_per_second: float = 5.0):
        self.max_per_second = max_per_second
        self.min_interval = 1.0 / max_per_second
        self._last_call: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Attend si necessaire pour respecter le rate limit."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_call

            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)

            self._last_call = asyncio.get_event_loop().time()


# =============================================================================
# LOG MANAGER
# =============================================================================

class LogManager:
    """
    Gestionnaire de logs centralise pour le bot Discord Minecraft.

    Gere l'ecriture des logs sur 3 canaux:
    - Fichiers (rotation quotidienne, compression apres 7 jours, retention 90 jours)
    - Base de donnees (batch insert pour performance)
    - Discord (channels configurables par niveau, rate limiting)

    Example:
        >>> log_manager = LogManager(bot, db_pool, log_dir="logs")
        >>> await log_manager.start()
        >>> await log_manager.info("Bot demarre", module="system")
        >>> await log_manager.stop()
    """

    # Configuration par defaut
    DEFAULT_RETENTION_DAYS = 90
    DEFAULT_COMPRESSION_DAYS = 7
    DEFAULT_BATCH_SIZE = 100
    DEFAULT_BATCH_TIMEOUT = 5.0  # secondes
    DEFAULT_RATE_LIMIT = 5.0  # messages/seconde

    def __init__(
        self,
        bot: Any,
        db_pool: Any = None,
        log_dir: str = "logs",
        retention_days: int = DEFAULT_RETENTION_DAYS,
        compression_days: int = DEFAULT_COMPRESSION_DAYS,
        min_level: LogLevel = LogLevel.DEBUG,
    ) -> None:
        """
        Initialise le gestionnaire de logs.

        Args:
            bot: Instance du bot Discord
            db_pool: Pool de connexions asyncpg a PostgreSQL
            log_dir: Chemin du dossier des fichiers de logs
            retention_days: Nombre de jours de retention (defaut: 90)
            compression_days: Jours avant compression gzip (defaut: 7)
            min_level: Niveau minimum de log a traiter
        """
        self.bot = bot
        self.db_pool = db_pool
        self.log_dir = Path(log_dir)
        self.retention_days = retention_days
        self.compression_days = compression_days
        self.min_level = min_level

        # Channels Discord par niveau
        self._discord_channels: Dict[LogLevel, int] = {}

        # Buffer pour batch insert DB
        self._db_buffer: List[LogEntry] = []
        self._db_buffer_lock = asyncio.Lock()

        # Queue pour Discord (async)
        self._discord_queue: asyncio.Queue[LogEntry] = asyncio.Queue()

        # Rate limiter Discord
        self._rate_limiter = RateLimiter(self.DEFAULT_RATE_LIMIT)

        # Tasks de fond
        self._tasks: List[asyncio.Task] = []
        self._stopping = False

        # Fichier de log courant
        self._current_file_date: Optional[str] = None
        self._current_file: Optional[aiofiles.threadpool.text.AsyncTextIOWrapper] = None
        self._file_lock = asyncio.Lock()

        # Statistiques
        self._stats = {
            "total_logged": 0,
            "by_level": {level.name: 0 for level in LogLevel},
            "by_module": {},
            "errors": {"file": 0, "db": 0, "discord": 0},
            "started_at": None,
        }

        logger.info(
            f"LogManager initialise (log_dir={log_dir}, retention={retention_days}d, "
            f"compression={compression_days}d, min_level={min_level.name})"
        )

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    def set_discord_channel(self, level: LogLevel, channel_id: int) -> None:
        """Configure le channel Discord pour un niveau de log specifique."""
        self._discord_channels[level] = channel_id
        logger.info(f"Channel Discord configure pour {level.name}: {channel_id}")

    def set_discord_channels(self, channels: Dict[LogLevel, int]) -> None:
        """Configure plusieurs channels Discord a la fois."""
        self._discord_channels.update(channels)
        for level, channel_id in channels.items():
            logger.info(f"Channel Discord configure pour {level.name}: {channel_id}")

    def get_discord_channel_for_level(self, level: LogLevel) -> Optional[int]:
        """
        Retourne le channel Discord pour un niveau donne.
        Cherche le channel exact ou le niveau superieur le plus proche.
        """
        if level in self._discord_channels:
            return self._discord_channels[level]

        # Chercher un niveau superieur
        for check_level in sorted(self._discord_channels.keys(), key=lambda x: x.value):
            if check_level.value <= level.value:
                return self._discord_channels[check_level]

        return None

    # =========================================================================
    # DEMARRAGE ET ARRET
    # =========================================================================

    async def start(self) -> None:
        """
        Demarre le gestionnaire de logs et toutes les taches de fond.
        """
        self._stopping = False
        self._stats["started_at"] = datetime.now().isoformat()

        # Creer le dossier de logs
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Demarrer les taches de fond
        self._tasks = [
            asyncio.create_task(self._db_flush_worker(), name="db_flush"),
            asyncio.create_task(self._discord_worker(), name="discord_sender"),
            asyncio.create_task(self._cleanup_worker(), name="cleanup"),
        ]

        logger.info("LogManager demarre avec succes")
        await self.info("Systeme de logs demarre", module="log_manager")

    async def stop(self) -> None:
        """
        Arrete proprement le gestionnaire de logs.
        Flush les buffers et ferme les fichiers.
        """
        if self._stopping:
            return

        self._stopping = True
        await self.info("Arret du systeme de logs...", module="log_manager")

        # Vider le buffer DB
        await self._flush_db_buffer()

        # Attendre que la queue Discord soit vide (max 10 secondes)
        if not self._discord_queue.empty():
            try:
                await asyncio.wait_for(self._discord_queue.join(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Timeout lors du vidage de la queue Discord")

        # Annuler les taches
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Fermer le fichier courant
        async with self._file_lock:
            if self._current_file:
                await self._current_file.close()
                self._current_file = None

        logger.info("LogManager arrete")

    # =========================================================================
    # METHODES DE LOG PRINCIPALES
    # =========================================================================

    async def log(
        self,
        level: LogLevel,
        message: str,
        module: Optional[str] = None,
        exc_info: Optional[BaseException] = None,
        guild_id: Optional[int] = None,
        user_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        **extra: Any,
    ) -> None:
        """
        Log une entree sur tous les canaux configures.

        Args:
            level: Niveau du log
            message: Message a logger
            module: Module source (defaut: "general")
            exc_info: Exception a inclure dans le log
            guild_id: ID du serveur Discord (optionnel)
            user_id: ID de l'utilisateur Discord (optionnel)
            channel_id: ID du channel Discord (optionnel)
            **extra: Donnees additionnelles
        """
        # Verifier le niveau minimum
        if level.value < self.min_level.value:
            return

        # Traiter l'exception si presente
        if exc_info:
            tb = "".join(traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__))
            extra["exception"] = {
                "type": type(exc_info).__name__,
                "message": str(exc_info),
                "traceback": tb,
            }
            if not message.endswith(str(exc_info)):
                message = f"{message}: {exc_info}"

        # Creer l'entree
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            module=module or "general",
            message=message,
            guild_id=guild_id,
            user_id=user_id,
            channel_id=channel_id,
            extra_data=extra if extra else None,
        )

        # Mettre a jour les statistiques
        self._stats["total_logged"] += 1
        self._stats["by_level"][level.name] += 1
        self._stats["by_module"][entry.module] = self._stats["by_module"].get(entry.module, 0) + 1

        # Ecrire sur les differents canaux (en parallele quand possible)
        tasks = [
            self._write_to_file(entry),
            self._add_to_db_buffer(entry),
        ]

        # Discord seulement si un channel est configure pour ce niveau
        if self.get_discord_channel_for_level(level):
            await self._discord_queue.put(entry)

        # Executer les ecritures fichier et DB
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                channel_name = ["file", "db"][i]
                self._stats["errors"][channel_name] += 1
                logger.error(f"Erreur ecriture {channel_name}: {result}")

    async def debug(
        self,
        message: str,
        module: Optional[str] = None,
        **extra: Any,
    ) -> None:
        """Log un message de niveau DEBUG."""
        await self.log(LogLevel.DEBUG, message, module=module, **extra)

    async def info(
        self,
        message: str,
        module: Optional[str] = None,
        **extra: Any,
    ) -> None:
        """Log un message de niveau INFO."""
        await self.log(LogLevel.INFO, message, module=module, **extra)

    async def warning(
        self,
        message: str,
        module: Optional[str] = None,
        **extra: Any,
    ) -> None:
        """Log un message de niveau WARNING."""
        await self.log(LogLevel.WARNING, message, module=module, **extra)

    async def error(
        self,
        message: str,
        module: Optional[str] = None,
        exc_info: Optional[BaseException] = None,
        **extra: Any,
    ) -> None:
        """Log un message de niveau ERROR."""
        await self.log(LogLevel.ERROR, message, module=module, exc_info=exc_info, **extra)

    async def critical(
        self,
        message: str,
        module: Optional[str] = None,
        exc_info: Optional[BaseException] = None,
        **extra: Any,
    ) -> None:
        """Log un message de niveau CRITICAL."""
        await self.log(LogLevel.CRITICAL, message, module=module, exc_info=exc_info, **extra)

    async def log_action(
        self,
        action: str,
        user: discord.User,
        guild: discord.Guild,
        details: Dict[str, Any],
        level: LogLevel = LogLevel.INFO,
    ) -> None:
        """
        Log une action Discord avec contexte complet.

        Args:
            action: Description de l'action (ex: "command_used", "member_banned")
            user: Utilisateur Discord
            guild: Serveur Discord
            details: Details de l'action
            level: Niveau de log (defaut: INFO)
        """
        await self.log(
            level=level,
            message=f"Action: {action}",
            module="discord",
            guild_id=guild.id if guild else None,
            user_id=user.id if user else None,
            action=action,
            user_name=str(user) if user else None,
            guild_name=guild.name if guild else None,
            **details,
        )

    # =========================================================================
    # ECRITURE FICHIERS
    # =========================================================================

    def _get_log_file_path(self, date: datetime) -> Path:
        """
        Retourne le chemin du fichier de log pour une date donnee.
        Format: logs/YYYY/MM/bot-YYYY-MM-DD.log
        """
        year = date.strftime("%Y")
        month = date.strftime("%m")
        filename = f"bot-{date.strftime('%Y-%m-%d')}.log"
        return self.log_dir / year / month / filename

    async def _write_to_file(self, entry: LogEntry) -> None:
        """Ecrit une entree dans le fichier de log du jour."""
        async with self._file_lock:
            # Verifier si on doit changer de fichier (nouveau jour)
            current_date = entry.timestamp.strftime("%Y-%m-%d")

            if current_date != self._current_file_date:
                # Fermer l'ancien fichier
                if self._current_file:
                    await self._current_file.close()

                # Creer le dossier si necessaire
                file_path = self._get_log_file_path(entry.timestamp)
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Ouvrir le nouveau fichier
                self._current_file = await aiofiles.open(
                    file_path,
                    mode="a",
                    encoding="utf-8"
                )
                self._current_file_date = current_date
                logger.debug(f"Nouveau fichier de log: {file_path}")

            # Ecrire l'entree
            line = entry.format_file() + "\n"
            await self._current_file.write(line)
            await self._current_file.flush()

    # =========================================================================
    # ECRITURE BASE DE DONNEES (BATCH INSERT)
    # =========================================================================

    async def _add_to_db_buffer(self, entry: LogEntry) -> None:
        """Ajoute une entree au buffer DB pour batch insert."""
        if not self.db_pool:
            return

        async with self._db_buffer_lock:
            self._db_buffer.append(entry)

            # Flush si le buffer est plein
            if len(self._db_buffer) >= self.DEFAULT_BATCH_SIZE:
                await self._flush_db_buffer()

    async def _flush_db_buffer(self) -> None:
        """Flush le buffer vers la base de donnees."""
        if not self.db_pool or not self._db_buffer:
            return

        async with self._db_buffer_lock:
            if not self._db_buffer:
                return

            entries = self._db_buffer.copy()
            self._db_buffer.clear()

        try:
            async with self.db_pool.acquire() as conn:
                # Preparer les donnees pour batch insert
                values = [
                    (
                        e.timestamp,
                        e.level.name,
                        e.module,
                        e.message,
                        json.dumps(e.extra_data) if e.extra_data else None,
                        e.guild_id,
                        e.user_id,
                        e.channel_id,
                    )
                    for e in entries
                ]

                # Batch insert
                await conn.executemany(
                    """
                    INSERT INTO logs.bot_logs
                        (timestamp, level, module, message, extra_data, guild_id, user_id, channel_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    values
                )

                logger.debug(f"Flush DB: {len(entries)} entrees inserees")

        except Exception as e:
            self._stats["errors"]["db"] += len(entries)
            logger.error(f"Erreur batch insert DB: {e}")
            # Remettre les entrees dans le buffer pour retry
            async with self._db_buffer_lock:
                self._db_buffer = entries + self._db_buffer

    async def _db_flush_worker(self) -> None:
        """Worker qui flush le buffer DB periodiquement."""
        while not self._stopping:
            try:
                await asyncio.sleep(self.DEFAULT_BATCH_TIMEOUT)
                if self._db_buffer:
                    await self._flush_db_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erreur db_flush_worker: {e}")

    # =========================================================================
    # ENVOI DISCORD
    # =========================================================================

    async def _discord_worker(self) -> None:
        """Worker qui envoie les logs vers Discord avec rate limiting."""
        while not self._stopping or not self._discord_queue.empty():
            try:
                # Attendre une entree avec timeout
                try:
                    entry = await asyncio.wait_for(
                        self._discord_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Envoyer sur Discord avec rate limiting
                await self._send_to_discord(entry)
                self._discord_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erreur discord_worker: {e}")

    async def _send_to_discord(self, entry: LogEntry) -> None:
        """Envoie une entree vers le channel Discord configure."""
        channel_id = self.get_discord_channel_for_level(entry.level)
        if not channel_id:
            return

        if not self.bot.is_ready():
            return

        try:
            # Rate limiting
            await self._rate_limiter.acquire()

            channel = self.bot.get_channel(channel_id)
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except discord.NotFound:
                    logger.warning(f"Channel Discord introuvable: {channel_id}")
                    return

            # Envoyer l'embed
            embed = entry.to_embed()
            await channel.send(embed=embed)

        except discord.HTTPException as e:
            self._stats["errors"]["discord"] += 1
            logger.warning(f"Erreur envoi Discord: {e}")
        except Exception as e:
            self._stats["errors"]["discord"] += 1
            logger.error(f"Erreur envoi Discord: {e}")

    # =========================================================================
    # RECHERCHE DE LOGS
    # =========================================================================

    async def search(
        self,
        level: Optional[LogLevel] = None,
        module: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        keyword: Optional[str] = None,
        guild_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LogEntry]:
        """
        Recherche des logs selon differents criteres.

        Args:
            level: Filtrer par niveau de log
            module: Filtrer par module source
            start_date: Date de debut
            end_date: Date de fin
            keyword: Mot-cle a rechercher dans le message
            guild_id: Filtrer par serveur Discord
            user_id: Filtrer par utilisateur Discord
            limit: Nombre maximum de resultats (defaut: 100)
            offset: Decalage pour pagination

        Returns:
            Liste des entrees de log correspondantes
        """
        # Essayer d'abord la base de donnees
        if self.db_pool:
            try:
                return await self._search_db(
                    level, module, start_date, end_date,
                    keyword, guild_id, user_id, limit, offset
                )
            except Exception as e:
                logger.warning(f"Recherche DB echouee, fallback fichiers: {e}")

        # Fallback: recherche dans les fichiers
        return await self._search_files(
            level, module, start_date, end_date,
            keyword, guild_id, user_id, limit, offset
        )

    async def _search_db(
        self,
        level: Optional[LogLevel],
        module: Optional[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        keyword: Optional[str],
        guild_id: Optional[int],
        user_id: Optional[int],
        limit: int,
        offset: int,
    ) -> List[LogEntry]:
        """Recherche dans la base de donnees PostgreSQL."""
        conditions = []
        params = []
        param_idx = 1

        if level:
            conditions.append(f"level = ${param_idx}")
            params.append(level.name)
            param_idx += 1

        if module:
            conditions.append(f"module = ${param_idx}")
            params.append(module)
            param_idx += 1

        if start_date:
            conditions.append(f"timestamp >= ${param_idx}")
            params.append(start_date)
            param_idx += 1

        if end_date:
            conditions.append(f"timestamp <= ${param_idx}")
            params.append(end_date)
            param_idx += 1

        if keyword:
            conditions.append(f"message ILIKE ${param_idx}")
            params.append(f"%{keyword}%")
            param_idx += 1

        if guild_id:
            conditions.append(f"guild_id = ${param_idx}")
            params.append(guild_id)
            param_idx += 1

        if user_id:
            conditions.append(f"user_id = ${param_idx}")
            params.append(user_id)
            param_idx += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = f"""
            SELECT id, timestamp, level, module, message, extra_data, guild_id, user_id, channel_id
            FROM logs.bot_logs
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [LogEntry.from_db_row(tuple(row)) for row in rows]

    async def _search_files(
        self,
        level: Optional[LogLevel],
        module: Optional[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        keyword: Optional[str],
        guild_id: Optional[int],
        user_id: Optional[int],
        limit: int,
        offset: int,
    ) -> List[LogEntry]:
        """Recherche dans les fichiers de logs."""
        entries: List[LogEntry] = []
        skipped = 0

        # Determiner la plage de dates
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()

        # Parcourir les fichiers
        current_date = start_date.date()
        while current_date <= end_date.date():
            file_path = self._get_log_file_path(datetime.combine(current_date, datetime.min.time()))

            # Verifier aussi les fichiers compresses
            gz_path = file_path.with_suffix(".log.gz")

            for path in [file_path, gz_path]:
                if not path.exists():
                    continue

                try:
                    if path.suffix == ".gz":
                        with gzip.open(path, "rt", encoding="utf-8") as f:
                            lines = f.readlines()
                    else:
                        async with aiofiles.open(path, "r", encoding="utf-8") as f:
                            lines = await f.readlines()

                    for line in lines:
                        entry = self._parse_log_line(line.strip())
                        if not entry:
                            continue

                        # Appliquer les filtres
                        if level and entry.level != level:
                            continue
                        if module and entry.module != module:
                            continue
                        if keyword and keyword.lower() not in entry.message.lower():
                            continue
                        if guild_id and entry.guild_id != guild_id:
                            continue
                        if user_id and entry.user_id != user_id:
                            continue
                        if entry.timestamp < start_date or entry.timestamp > end_date:
                            continue

                        # Gerer offset
                        if skipped < offset:
                            skipped += 1
                            continue

                        entries.append(entry)
                        if len(entries) >= limit:
                            return entries

                except Exception as e:
                    logger.warning(f"Erreur lecture fichier {path}: {e}")

            current_date += timedelta(days=1)

        return entries

    def _parse_log_line(self, line: str) -> Optional[LogEntry]:
        """Parse une ligne de fichier de log."""
        if not line:
            return None

        try:
            import re

            # Format: [YYYY-MM-DD HH:mm:ss.fff] [LEVEL   ] [module] message | meta
            pattern = r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\] \[(\w+)\s*\] \[([^\]]+)\] (.+?)(?:\s*\|\s*(.+))?$"
            match = re.match(pattern, line)

            if not match:
                return None

            timestamp_str, level_str, module, message, meta_str = match.groups()
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")

            # Parser les metadonnees
            guild_id = user_id = channel_id = None
            extra_data = {}

            if meta_str:
                for part in meta_str.split():
                    if "=" in part:
                        key, value = part.split("=", 1)
                        if key == "guild":
                            guild_id = int(value)
                        elif key == "user":
                            user_id = int(value)
                        elif key == "channel":
                            channel_id = int(value)
                        elif key == "extra":
                            try:
                                extra_data = json.loads(value)
                            except json.JSONDecodeError:
                                pass

            return LogEntry(
                timestamp=timestamp,
                level=LogLevel.from_string(level_str),
                module=module,
                message=message,
                guild_id=guild_id,
                user_id=user_id,
                channel_id=channel_id,
                extra_data=extra_data,
            )

        except Exception as e:
            logger.debug(f"Erreur parsing ligne de log: {e}")
            return None

    # =========================================================================
    # EXPORT DE LOGS
    # =========================================================================

    async def export_logs(
        self,
        format: Literal["json", "csv", "txt"] = "json",
        level: Optional[LogLevel] = None,
        module: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        keyword: Optional[str] = None,
        **filters: Any,
    ) -> bytes:
        """
        Exporte les logs dans le format specifie.

        Args:
            format: Format d'export (json, csv, txt)
            level: Filtrer par niveau
            module: Filtrer par module
            start_date: Date de debut
            end_date: Date de fin
            keyword: Mot-cle a rechercher
            **filters: Filtres additionnels

        Returns:
            Contenu du fichier exporte en bytes
        """
        # Recuperer les logs
        entries = await self.search(
            level=level,
            module=module,
            start_date=start_date,
            end_date=end_date,
            keyword=keyword,
            limit=100000,  # Limite haute pour export
            **{k: v for k, v in filters.items() if k in ["guild_id", "user_id"]},
        )

        if format == "json":
            return self._export_json(entries)
        elif format == "csv":
            return self._export_csv(entries)
        else:
            return self._export_txt(entries)

    def _export_json(self, entries: List[LogEntry]) -> bytes:
        """Exporte en JSON."""
        data = {
            "exported_at": datetime.now().isoformat(),
            "count": len(entries),
            "entries": [e.to_dict() for e in entries],
        }
        return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")

    def _export_csv(self, entries: List[LogEntry]) -> bytes:
        """Exporte en CSV."""
        import csv

        output = io.StringIO()
        writer = csv.writer(output)

        # En-tetes
        writer.writerow([
            "id", "timestamp", "level", "module", "message",
            "guild_id", "user_id", "channel_id", "extra_data"
        ])

        # Donnees
        for entry in entries:
            writer.writerow([
                entry.id or "",
                entry.timestamp.isoformat(),
                entry.level.name,
                entry.module,
                entry.message,
                entry.guild_id or "",
                entry.user_id or "",
                entry.channel_id or "",
                json.dumps(entry.extra_data) if entry.extra_data else "",
            ])

        return output.getvalue().encode("utf-8")

    def _export_txt(self, entries: List[LogEntry]) -> bytes:
        """Exporte en texte brut."""
        lines = [entry.format_file() for entry in entries]
        return "\n".join(lines).encode("utf-8")

    # =========================================================================
    # STATISTIQUES
    # =========================================================================

    async def get_stats(self, period: Literal["day", "week", "month"] = "day") -> Dict[str, Any]:
        """
        Retourne les statistiques des logs.

        Args:
            period: Periode (day, week, month)

        Returns:
            Dictionnaire avec:
            - counts par level
            - top modules
            - erreurs frequentes
        """
        # Calculer les dates
        end_date = datetime.now()
        if period == "day":
            start_date = end_date - timedelta(days=1)
        elif period == "week":
            start_date = end_date - timedelta(weeks=1)
        else:
            start_date = end_date - timedelta(days=30)

        stats = {
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "session": dict(self._stats),
        }

        # Stats de la DB si disponible
        if self.db_pool:
            try:
                stats["database"] = await self._get_db_stats(start_date, end_date)
            except Exception as e:
                logger.warning(f"Erreur recuperation stats DB: {e}")
                stats["database"] = None

        # Stats des fichiers
        stats["files"] = await self._get_file_stats()

        return stats

    async def _get_db_stats(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Recupere les statistiques depuis la base de donnees."""
        async with self.db_pool.acquire() as conn:
            # Total par niveau
            by_level = await conn.fetch(
                """
                SELECT level, COUNT(*) as count
                FROM logs.bot_logs
                WHERE timestamp >= $1 AND timestamp <= $2
                GROUP BY level
                """,
                start_date, end_date
            )

            # Top modules
            top_modules = await conn.fetch(
                """
                SELECT module, COUNT(*) as count
                FROM logs.bot_logs
                WHERE timestamp >= $1 AND timestamp <= $2
                GROUP BY module
                ORDER BY count DESC
                LIMIT 10
                """,
                start_date, end_date
            )

            # Erreurs frequentes
            frequent_errors = await conn.fetch(
                """
                SELECT LEFT(message, 100) as message, COUNT(*) as count
                FROM logs.bot_logs
                WHERE timestamp >= $1 AND timestamp <= $2
                AND level IN ('ERROR', 'CRITICAL')
                GROUP BY LEFT(message, 100)
                ORDER BY count DESC
                LIMIT 10
                """,
                start_date, end_date
            )

            # Total
            total = await conn.fetchval(
                """
                SELECT COUNT(*) FROM logs.bot_logs
                WHERE timestamp >= $1 AND timestamp <= $2
                """,
                start_date, end_date
            )

            return {
                "total": total or 0,
                "by_level": {row["level"]: row["count"] for row in by_level},
                "top_modules": [{"module": row["module"], "count": row["count"]} for row in top_modules],
                "frequent_errors": [{"message": row["message"], "count": row["count"]} for row in frequent_errors],
            }

    async def _get_file_stats(self) -> Dict[str, Any]:
        """Statistiques sur les fichiers de logs."""
        total_size = 0
        file_count = 0
        compressed_count = 0
        oldest_file = None
        newest_file = None

        for log_file in self.log_dir.rglob("*.log"):
            try:
                stat = log_file.stat()
                total_size += stat.st_size
                file_count += 1

                # Extraire la date du nom de fichier
                date_match = log_file.stem.replace("bot-", "")
                try:
                    file_date = datetime.strptime(date_match, "%Y-%m-%d")
                    if oldest_file is None or file_date < oldest_file:
                        oldest_file = file_date
                    if newest_file is None or file_date > newest_file:
                        newest_file = file_date
                except ValueError:
                    pass

            except OSError:
                continue

        for gz_file in self.log_dir.rglob("*.log.gz"):
            try:
                total_size += gz_file.stat().st_size
                compressed_count += 1
            except OSError:
                continue

        return {
            "log_files": file_count,
            "compressed_files": compressed_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_file": oldest_file.isoformat() if oldest_file else None,
            "newest_file": newest_file.isoformat() if newest_file else None,
        }

    # =========================================================================
    # CLEANUP ET COMPRESSION
    # =========================================================================

    async def _cleanup_worker(self) -> None:
        """Worker qui effectue le cleanup toutes les heures."""
        while not self._stopping:
            try:
                await asyncio.sleep(3600)  # 1 heure
                await self._run_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erreur cleanup_worker: {e}")

    async def _run_cleanup(self) -> None:
        """Execute le cleanup: compression et suppression des vieux logs."""
        logger.info("Demarrage du cleanup des logs...")

        compressed = 0
        deleted = 0
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        compression_date = datetime.now() - timedelta(days=self.compression_days)

        for log_file in self.log_dir.rglob("*.log"):
            try:
                # Extraire la date du nom
                date_match = log_file.stem.replace("bot-", "")
                try:
                    file_date = datetime.strptime(date_match, "%Y-%m-%d")
                except ValueError:
                    continue

                # Supprimer si trop vieux
                if file_date < cutoff_date:
                    log_file.unlink()
                    deleted += 1
                    logger.debug(f"Fichier supprime: {log_file}")
                    continue

                # Compresser si assez vieux
                if file_date < compression_date:
                    gz_path = log_file.with_suffix(".log.gz")
                    if not gz_path.exists():
                        await self._compress_file(log_file, gz_path)
                        log_file.unlink()
                        compressed += 1
                        logger.debug(f"Fichier compresse: {log_file} -> {gz_path}")

            except Exception as e:
                logger.warning(f"Erreur traitement fichier {log_file}: {e}")

        # Supprimer les fichiers compresses trop vieux
        for gz_file in self.log_dir.rglob("*.log.gz"):
            try:
                date_match = gz_file.stem.replace("bot-", "").replace(".log", "")
                file_date = datetime.strptime(date_match, "%Y-%m-%d")

                if file_date < cutoff_date:
                    gz_file.unlink()
                    deleted += 1
            except (ValueError, OSError) as e:
                logger.warning(f"Erreur suppression {gz_file}: {e}")

        if compressed or deleted:
            await self.info(
                f"Cleanup termine: {compressed} fichiers compresses, {deleted} fichiers supprimes",
                module="log_manager",
                compressed=compressed,
                deleted=deleted,
            )

    async def _compress_file(self, src: Path, dst: Path) -> None:
        """Compresse un fichier avec gzip."""
        async with aiofiles.open(src, "rb") as f_in:
            content = await f_in.read()

        with gzip.open(dst, "wb") as f_out:
            f_out.write(content)

    async def force_cleanup(self) -> Dict[str, int]:
        """
        Force un cleanup immediat.

        Returns:
            Statistiques du cleanup
        """
        await self._run_cleanup()
        return {"status": "completed"}


# =============================================================================
# HELPER POUR CREER LE LOG MANAGER
# =============================================================================

async def create_log_manager(
    bot: Any,
    db_pool: Any = None,
    log_dir: str = "logs",
    discord_channels: Optional[Dict[LogLevel, int]] = None,
    **kwargs: Any,
) -> LogManager:
    """
    Factory function pour creer et demarrer un LogManager.

    Args:
        bot: Instance du bot Discord
        db_pool: Pool de connexions PostgreSQL (asyncpg)
        log_dir: Dossier des logs
        discord_channels: Mapping niveau -> channel_id Discord
        **kwargs: Arguments additionnels pour LogManager

    Returns:
        Instance de LogManager demarree
    """
    manager = LogManager(bot, db_pool, log_dir, **kwargs)

    if discord_channels:
        manager.set_discord_channels(discord_channels)

    await manager.start()
    return manager
