"""
Point d'entree principal du bot Discord Minecraft.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from src.config import settings
from src.core import MinecraftBot


def setup_logging() -> None:
    """Configure le systeme de logging."""
    # Configurer le logger racine
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format=settings.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Reduire le bruit des bibliotheques externes
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    # Logger principal de l'application
    logger = logging.getLogger("src")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    if settings.DEBUG:
        logging.getLogger("discord").setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)


def validate_config() -> bool:
    """Valide la configuration avant le demarrage."""
    logger = logging.getLogger(__name__)

    if not settings.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN n'est pas configure!")
        return False

    if settings.DISCORD_TOKEN == "your-discord-token-here":
        logger.error("DISCORD_TOKEN contient la valeur par defaut!")
        return False

    logger.info(f"Configuration validee pour '{settings.PROJECT_NAME}'")
    return True


async def run_bot() -> None:
    """Lance le bot de maniere asynchrone."""
    logger = logging.getLogger(__name__)

    bot: Optional[MinecraftBot] = None

    try:
        # Creer l'instance du bot
        bot = MinecraftBot()

        # Configurer les gestionnaires de signaux pour arret propre
        if sys.platform != "win32":
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(
                    sig,
                    lambda: asyncio.create_task(shutdown(bot)),
                )

        logger.info(f"Demarrage de {settings.PROJECT_NAME}...")

        # Lancer le bot
        async with bot:
            await bot.start(settings.DISCORD_TOKEN)

    except KeyboardInterrupt:
        logger.info("Interruption clavier detectee")
    except Exception as e:
        logger.exception(f"Erreur fatale: {e}")
        raise
    finally:
        if bot is not None and not bot.is_closed():
            await bot.close()


async def shutdown(bot: MinecraftBot) -> None:
    """Arrete proprement le bot."""
    logger = logging.getLogger(__name__)
    logger.info("Signal d'arret recu, fermeture en cours...")
    await bot.close()


def main() -> int:
    """Fonction principale."""
    # Configurer le logging
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info(f"  {settings.PROJECT_NAME} - Bot Discord Minecraft")
    logger.info("=" * 60)

    # Valider la configuration
    if not validate_config():
        logger.error("Configuration invalide, arret du bot")
        return 1

    # Lancer le bot
    try:
        asyncio.run(run_bot())
        return 0
    except KeyboardInterrupt:
        logger.info("Bot arrete par l'utilisateur")
        return 0
    except Exception as e:
        logger.exception(f"Erreur lors du demarrage: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
