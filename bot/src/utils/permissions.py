"""Systeme de permissions base sur les IDs de roles Discord."""
from enum import IntEnum
from functools import wraps
from typing import Callable, Optional
import discord
from discord import app_commands, Interaction

from src.config import settings


class PermissionLevel(IntEnum):
    """Niveaux de permission."""
    USER = 0
    VIP = 1
    MODERATOR = 2
    ADMIN = 3
    OWNER = 4


def get_permission_level(member: discord.Member) -> PermissionLevel:
    """
    Determine le niveau de permission d'un membre base sur ses roles (par ID).
    """
    # Owner check (par ID utilisateur)
    if member.id in settings.DISCORD_OWNER_IDS:
        return PermissionLevel.OWNER

    # Admin Discord (permission administrateur)
    if member.guild_permissions.administrator:
        return PermissionLevel.ADMIN

    # Recuperer les IDs des roles du membre
    role_ids = {role.id for role in member.roles}

    # Verifier par ID de role configure
    if settings.DISCORD_ADMIN_ROLE_ID and settings.DISCORD_ADMIN_ROLE_ID in role_ids:
        return PermissionLevel.ADMIN

    if settings.DISCORD_MOD_ROLE_ID and settings.DISCORD_MOD_ROLE_ID in role_ids:
        return PermissionLevel.MODERATOR

    if settings.DISCORD_VIP_ROLE_ID and settings.DISCORD_VIP_ROLE_ID in role_ids:
        return PermissionLevel.VIP

    return PermissionLevel.USER


def require_level(level: PermissionLevel):
    """Decorateur pour exiger un niveau de permission minimum."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, interaction: Interaction, *args, **kwargs):
            if not interaction.guild or not isinstance(interaction.user, discord.Member):
                await interaction.response.send_message(
                    "Cette commande ne peut etre utilisee que dans un serveur.",
                    ephemeral=True
                )
                return

            user_level = get_permission_level(interaction.user)

            if user_level < level:
                level_names = {
                    PermissionLevel.VIP: "VIP",
                    PermissionLevel.MODERATOR: "Moderateur",
                    PermissionLevel.ADMIN: "Administrateur",
                    PermissionLevel.OWNER: "Proprietaire",
                }
                await interaction.response.send_message(
                    f"Permission insuffisante. Niveau requis: **{level_names.get(level, 'Inconnu')}**",
                    ephemeral=True
                )
                return

            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator


# Decorateurs pratiques
def require_vip(func: Callable):
    """Exige le niveau VIP ou superieur."""
    return require_level(PermissionLevel.VIP)(func)


def require_mod(func: Callable):
    """Exige le niveau Moderateur ou superieur."""
    return require_level(PermissionLevel.MODERATOR)(func)


def require_admin(func: Callable):
    """Exige le niveau Admin ou superieur."""
    return require_level(PermissionLevel.ADMIN)(func)


def require_owner(func: Callable):
    """Exige le niveau Owner."""
    return require_level(PermissionLevel.OWNER)(func)


# Check pour app_commands
def is_admin():
    """Check pour les commandes d'application."""
    async def predicate(interaction: Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False
        return get_permission_level(interaction.user) >= PermissionLevel.ADMIN
    return app_commands.check(predicate)


def is_mod():
    """Check pour les commandes necessitant moderateur."""
    async def predicate(interaction: Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False
        return get_permission_level(interaction.user) >= PermissionLevel.MODERATOR
    return app_commands.check(predicate)


def is_owner():
    """Check pour les commandes owner uniquement."""
    async def predicate(interaction: Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False
        return get_permission_level(interaction.user) >= PermissionLevel.OWNER
    return app_commands.check(predicate)
