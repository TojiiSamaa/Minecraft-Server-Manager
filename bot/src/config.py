"""
Configuration du bot via pydantic-settings.
Charge les variables d'environnement avec validation.
"""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration principale du bot Discord."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Identification du projet ===
    PROJECT_NAME: str = Field(
        default="MinecraftBot",
        description="Nom du bot (affiché dans les logs et le status)",
    )
    DEBUG: bool = Field(default=False, description="Mode debug")

    # === Discord ===
    DISCORD_TOKEN: str = Field(..., description="Token du bot Discord")
    DISCORD_PREFIX: str = Field(default="!", description="Préfixe des commandes")
    DISCORD_GUILD_ID: Optional[int] = Field(
        default=None, description="ID du serveur Discord principal"
    )
    DISCORD_OWNER_IDS: list[int] = Field(
        default_factory=list,
        description="Liste des IDs des propriétaires du bot"
    )
    DISCORD_ADMIN_ROLE_ID: Optional[int] = Field(
        default=None,
        description="ID du rôle Admin Discord"
    )
    DISCORD_MOD_ROLE_ID: Optional[int] = Field(
        default=None,
        description="ID du rôle Modérateur Discord"
    )
    DISCORD_VIP_ROLE_ID: Optional[int] = Field(
        default=None,
        description="ID du rôle VIP Discord"
    )

    # === Base de données ===
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./data/bot.db",
        description="URL de connexion à la base de données",
    )
    DATABASE_ECHO: bool = Field(
        default=False, description="Afficher les requêtes SQL"
    )

    # === Redis ===
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="URL de connexion Redis",
    )
    REDIS_PREFIX: str = Field(
        default="mcbot:", description="Préfixe des clés Redis"
    )

    # === Minecraft RCON ===
    RCON_HOST: str = Field(
        default="localhost", description="Hôte du serveur Minecraft"
    )
    RCON_PORT: int = Field(default=25575, description="Port RCON")
    RCON_PASSWORD: str = Field(default="", description="Mot de passe RCON")
    RCON_TIMEOUT: float = Field(default=5.0, description="Timeout RCON en secondes")

    # === Minecraft Query ===
    MINECRAFT_HOST: str = Field(
        default="localhost", description="Hôte du serveur Minecraft"
    )
    MINECRAFT_PORT: int = Field(default=25565, description="Port du serveur Minecraft")

    # === Cache ===
    CACHE_TTL: int = Field(
        default=60, description="Durée de vie du cache en secondes"
    )
    ONLINE_PLAYERS_CACHE_TTL: int = Field(
        default=30, description="TTL du cache des joueurs en ligne"
    )

    # === Logging ===
    LOG_LEVEL: str = Field(default="INFO", description="Niveau de log")
    LOG_FORMAT: str = Field(
        default="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        description="Format des logs",
    )

    @field_validator("DISCORD_OWNER_IDS", mode="before")
    @classmethod
    def parse_owner_ids(cls, v):
        """Parse les IDs des propriétaires depuis une string ou liste."""
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v or []

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Valide le niveau de log."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"LOG_LEVEL doit etre parmi {valid_levels}")
        return upper_v


# Instance singleton de la configuration
settings = Settings()
