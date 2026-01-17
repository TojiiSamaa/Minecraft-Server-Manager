"""
Classe principale du bot Discord pour serveur Minecraft.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import discord
from discord.ext import commands, tasks

from src.config import settings
from src.utils.sanitize import sanitize_url, SanitizedLoggerAdapter

# Configuration du logger avec sanitization automatique
_logger = logging.getLogger(__name__)
logger = SanitizedLoggerAdapter(_logger)


class MinecraftBot(commands.Bot):
    """
    Bot Discord principal pour la gestion d'un serveur Minecraft.

    Fonctionnalites:
    - Connexion automatique a la base de donnees, Redis et RCON
    - Chargement automatique des cogs
    - Cache des joueurs en ligne
    - Gestion des evenements Discord
    - Mise a jour du status Discord
    """

    def __init__(self) -> None:
        """Initialise le bot avec la configuration."""
        # Configuration des intents Discord
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        # Initialisation de la classe parente
        super().__init__(
            command_prefix=self._get_prefix,
            intents=intents,
            help_command=commands.DefaultHelpCommand(),
            case_insensitive=True,
            owner_ids=set(settings.DISCORD_OWNER_IDS) if settings.DISCORD_OWNER_IDS else None,
        )

        # Nom du bot configurable
        self.bot_name: str = settings.PROJECT_NAME

        # Horodatage de demarrage
        self.start_time: Optional[datetime] = None

        # Connexions externes (initialisees dans setup_hook)
        self.db_session: Any = None  # Session SQLAlchemy async
        self.redis: Any = None  # Client Redis async
        self.rcon: Any = None  # Client RCON

        # Cache des joueurs en ligne
        self._online_players_cache: dict[str, Any] = {
            "players": [],
            "count": 0,
            "max": 0,
            "last_update": None,
        }
        self._cache_lock = asyncio.Lock()

        # Flag pour la fermeture propre
        self._closing = False

        logger.info(f"Bot '{self.bot_name}' initialise")

    async def _get_prefix(
        self, bot: commands.Bot, message: discord.Message
    ) -> list[str]:
        """
        Retourne les prefixes de commande.
        Peut etre etendu pour des prefixes par serveur.
        """
        prefixes = [settings.DISCORD_PREFIX]
        # Permet aussi de mentionner le bot comme prefixe
        return commands.when_mentioned_or(*prefixes)(bot, message)

    # =========================================================================
    # SETUP ET CONNEXIONS
    # =========================================================================

    async def setup_hook(self) -> None:
        """
        Configure le bot apres la connexion.
        Appele automatiquement par discord.py.
        """
        logger.info("Demarrage de la configuration du bot...")

        # Initialiser les connexions en parallele
        await asyncio.gather(
            self._setup_database(),
            self._setup_redis(),
            self._setup_rcon(),
        )

        # Charger les cogs
        await self._load_all_cogs()

        # Demarrer les taches de fond
        self._start_background_tasks()

        logger.info("Configuration du bot terminee")

    async def _setup_database(self) -> None:
        """Configure la connexion a la base de donnees."""
        try:
            from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
            from sqlalchemy.orm import sessionmaker

            engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DATABASE_ECHO,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_pre_ping=True,
                pool_recycle=1800,
            )
            async_session = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            self.db_session = async_session
            logger.info(f"Connexion base de donnees etablie: {sanitize_url(settings.DATABASE_URL)}")
        except ImportError:
            logger.warning("SQLAlchemy non installe, base de donnees desactivee")
        except Exception as e:
            logger.error(f"Erreur connexion base de donnees: {e}")

    async def _setup_redis(self) -> None:
        """Configure la connexion Redis."""
        try:
            import redis.asyncio as aioredis

            self.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test de connexion
            await self.redis.ping()
            logger.info(f"Connexion Redis etablie: {sanitize_url(settings.REDIS_URL)}")
        except ImportError:
            logger.warning("redis-py non installe, Redis desactive")
        except Exception as e:
            logger.error(f"Erreur connexion Redis: {e}")
            self.redis = None

    async def _setup_rcon(self) -> None:
        """Configure la connexion RCON au serveur Minecraft."""
        from src.core.rcon_client import RCONClient

        if not settings.RCON_PASSWORD:
            logger.warning("RCON desactive - mot de passe non configure")
            self.rcon = None
            return

        try:
            self.rcon = RCONClient(
                host=settings.RCON_HOST,
                port=settings.RCON_PORT,
                password=settings.RCON_PASSWORD,
                timeout=10.0,
                auto_reconnect=True,
            )
            await self.rcon.connect()
            logger.info("Connexion RCON etablie")
        except Exception as e:
            logger.error(f"Erreur connexion RCON: {e}")
            self.rcon = None

    async def execute_rcon(self, command: str) -> Optional[str]:
        """
        Execute une commande RCON sur le serveur Minecraft.

        Args:
            command: La commande a executer

        Returns:
            La reponse du serveur ou None en cas d'erreur
        """
        if self.rcon is None:
            logger.warning("RCON non configure")
            return None

        try:
            result = await self.rcon.execute(command)
            logger.debug(f"RCON '{command}': {result}")
            return result
        except Exception as e:
            logger.error(f"Erreur RCON: {e}")
            return None

    # =========================================================================
    # CHARGEMENT DES COGS
    # =========================================================================

    async def _load_all_cogs(self) -> None:
        """Charge automatiquement tous les cogs depuis le dossier cogs/."""
        cogs_dir = Path(__file__).parent.parent / "cogs"

        if not cogs_dir.exists():
            logger.warning(f"Dossier cogs non trouve: {cogs_dir}")
            cogs_dir.mkdir(parents=True, exist_ok=True)
            return

        loaded = 0
        for cog_file in cogs_dir.glob("*.py"):
            if cog_file.name.startswith("_"):
                continue

            cog_name = f"src.cogs.{cog_file.stem}"
            try:
                await self.load_extension(cog_name)
                logger.info(f"Cog charge: {cog_name}")
                loaded += 1
            except Exception as e:
                logger.error(f"Erreur chargement cog {cog_name}: {e}")

        logger.info(f"{loaded} cog(s) charge(s)")

    async def reload_cog(self, cog_name: str) -> bool:
        """
        Recharge un cog specifique.

        Args:
            cog_name: Nom du cog (sans le prefixe src.cogs.)

        Returns:
            True si le rechargement a reussi
        """
        full_name = f"src.cogs.{cog_name}"
        try:
            await self.reload_extension(full_name)
            logger.info(f"Cog recharge: {full_name}")
            return True
        except Exception as e:
            logger.error(f"Erreur rechargement cog {full_name}: {e}")
            return False

    # =========================================================================
    # CACHE DES JOUEURS EN LIGNE
    # =========================================================================

    async def get_online_players(self, force_refresh: bool = False) -> dict[str, Any]:
        """
        Retourne les informations sur les joueurs en ligne.
        Utilise un cache avec TTL configurable.

        Args:
            force_refresh: Forcer la mise a jour du cache

        Returns:
            Dict avec 'players', 'count', 'max', 'last_update'
        """
        async with self._cache_lock:
            now = datetime.now()
            last_update = self._online_players_cache.get("last_update")

            # Verifier si le cache est valide
            cache_valid = (
                last_update is not None
                and (now - last_update).total_seconds() < settings.ONLINE_PLAYERS_CACHE_TTL
            )

            if not force_refresh and cache_valid:
                return self._online_players_cache.copy()

            # Rafraichir le cache
            await self._refresh_online_players_cache()
            return self._online_players_cache.copy()

    async def _refresh_online_players_cache(self) -> None:
        """Rafraichit le cache des joueurs en ligne via RCON ou Query."""
        try:
            # Essayer d'abord via RCON
            result = await self.execute_rcon("list")
            if result:
                # Parser la reponse "There are X of Y players online: player1, player2"
                players = []
                count = 0
                max_players = 0

                if "players online" in result.lower():
                    parts = result.split(":")
                    if len(parts) >= 1:
                        # Extraire le nombre de joueurs
                        import re
                        match = re.search(r"(\d+)\s+of\s+(\d+)", parts[0])
                        if match:
                            count = int(match.group(1))
                            max_players = int(match.group(2))

                        # Extraire la liste des joueurs
                        if len(parts) >= 2 and parts[1].strip():
                            players = [p.strip() for p in parts[1].split(",") if p.strip()]

                self._online_players_cache = {
                    "players": players,
                    "count": count,
                    "max": max_players,
                    "last_update": datetime.now(),
                }
                logger.debug(f"Cache joueurs mis a jour: {count} joueur(s)")
                return

        except Exception as e:
            logger.error(f"Erreur mise a jour cache joueurs: {e}")

        # En cas d'echec, mettre a jour le timestamp pour eviter les requetes repetees
        self._online_players_cache["last_update"] = datetime.now()

    async def invalidate_players_cache(self) -> None:
        """Invalide le cache des joueurs en ligne."""
        async with self._cache_lock:
            self._online_players_cache["last_update"] = None
            logger.debug("Cache joueurs invalide")

    # =========================================================================
    # STATUS DISCORD
    # =========================================================================

    async def update_status(
        self,
        status: discord.Status = discord.Status.online,
        activity_type: discord.ActivityType = discord.ActivityType.playing,
        activity_name: Optional[str] = None,
    ) -> None:
        """
        Met a jour le status Discord du bot.

        Args:
            status: Status (online, idle, dnd, invisible)
            activity_type: Type d'activite (playing, watching, listening, streaming)
            activity_name: Texte de l'activite
        """
        if activity_name is None:
            # Status par defaut avec nombre de joueurs
            cache = await self.get_online_players()
            activity_name = f"Minecraft | {cache['count']} joueur(s)"

        activity = discord.Activity(type=activity_type, name=activity_name)
        await self.change_presence(status=status, activity=activity)
        logger.debug(f"Status mis a jour: {activity_name}")

    async def set_maintenance_status(self, message: str = "Maintenance en cours") -> None:
        """Met le bot en mode maintenance."""
        await self.update_status(
            status=discord.Status.dnd,
            activity_type=discord.ActivityType.playing,
            activity_name=message,
        )

    # =========================================================================
    # TACHES DE FOND
    # =========================================================================

    def _start_background_tasks(self) -> None:
        """Demarre les taches de fond."""
        self.update_status_task.start()
        logger.info("Taches de fond demarrees")

    @tasks.loop(minutes=2)
    async def update_status_task(self) -> None:
        """Tache de mise a jour periodique du status."""
        if self._closing:
            return
        try:
            await self.update_status()
        except Exception as e:
            logger.error(f"Erreur mise a jour status: {e}")

    @update_status_task.before_loop
    async def before_update_status(self) -> None:
        """Attend que le bot soit pret avant de demarrer la tache."""
        await self.wait_until_ready()

    # =========================================================================
    # EVENEMENTS DISCORD
    # =========================================================================

    async def on_ready(self) -> None:
        """Evenement appele quand le bot est connecte et pret."""
        self.start_time = datetime.now()

        logger.info("=" * 50)
        logger.info(f"Bot connecte: {self.user.name} ({self.user.id})")
        logger.info(f"Nom du projet: {self.bot_name}")
        logger.info(f"Serveurs: {len(self.guilds)}")
        logger.info(f"Prefix: {settings.DISCORD_PREFIX}")
        logger.info("=" * 50)

        # Mettre a jour le status initial
        await self.update_status()

        # Synchroniser les commandes slash si necessaire
        if settings.DISCORD_GUILD_ID:
            guild = discord.Object(id=settings.DISCORD_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Commandes synchronisees pour le serveur {settings.DISCORD_GUILD_ID}")

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """Gestion globale des erreurs d'evenements."""
        logger.exception(f"Erreur dans l'evenement {event_method}")

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        """Gestion des erreurs de commandes."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignorer les commandes inconnues

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Argument manquant: `{error.param.name}`")
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Vous n'avez pas les permissions necessaires.")
            return

        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send("Je n'ai pas les permissions necessaires.")
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"Commande en cooldown. Reessayez dans {error.retry_after:.1f}s"
            )
            return

        if isinstance(error, commands.CheckFailure):
            await ctx.send("Vous ne pouvez pas utiliser cette commande.")
            return

        # Erreur non geree
        logger.error(f"Erreur commande {ctx.command}: {error}", exc_info=error)
        await ctx.send("Une erreur est survenue lors de l'execution de la commande.")

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Evenement quand le bot rejoint un serveur."""
        logger.info(f"Bot ajoute au serveur: {guild.name} ({guild.id})")

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Evenement quand le bot quitte un serveur."""
        logger.info(f"Bot retire du serveur: {guild.name} ({guild.id})")

    # =========================================================================
    # UTILITAIRES
    # =========================================================================

    @property
    def uptime(self) -> Optional[float]:
        """Retourne le temps de fonctionnement en secondes."""
        if self.start_time is None:
            return None
        return (datetime.now() - self.start_time).total_seconds()

    def format_uptime(self) -> str:
        """Retourne le temps de fonctionnement formate."""
        seconds = self.uptime
        if seconds is None:
            return "N/A"

        days, remainder = divmod(int(seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days}j")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")

        return " ".join(parts)

    # =========================================================================
    # FERMETURE PROPRE
    # =========================================================================

    async def close(self) -> None:
        """Ferme proprement toutes les connexions et arrete le bot."""
        if self._closing:
            return

        self._closing = True
        logger.info("Fermeture du bot en cours...")

        # Arreter les taches de fond
        if self.update_status_task.is_running():
            self.update_status_task.cancel()

        # Fermer Redis
        if self.redis is not None:
            try:
                await self.redis.close()
                logger.info("Connexion Redis fermee")
            except Exception as e:
                logger.error(f"Erreur fermeture Redis: {e}")

        # Fermer la base de donnees
        if self.db_session is not None:
            try:
                # La session factory n'a pas besoin d'etre fermee explicitement
                logger.info("Connexion base de donnees fermee")
            except Exception as e:
                logger.error(f"Erreur fermeture DB: {e}")

        # Fermer RCON
        if self.rcon is not None:
            try:
                await self.rcon.disconnect()
                logger.info("Connexion RCON fermee")
            except Exception as e:
                logger.error(f"Erreur fermeture RCON: {e}")

        # Appeler la fermeture parente
        await super().close()
        logger.info("Bot ferme proprement")
