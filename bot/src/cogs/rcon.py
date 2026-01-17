"""
Cog RCON - Commandes pour interagir avec le serveur Minecraft via RCON.

Ce module fournit des commandes slash Discord pour exécuter des commandes
RCON sur un serveur Minecraft, avec autocomplete et gestion des permissions.
"""

import logging
from typing import Optional, List
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from src.utils.validators import (
    validate_minecraft_username,
    sanitize_rcon_input,
    is_dangerous_command,
    validate_rcon_command,
)

# Configuration du logger
logger = logging.getLogger(__name__)

# Liste des items Minecraft courants (liste partielle pour l'autocomplete)
MINECRAFT_ITEMS = [
    "diamond", "diamond_sword", "diamond_pickaxe", "diamond_axe", "diamond_shovel",
    "diamond_helmet", "diamond_chestplate", "diamond_leggings", "diamond_boots",
    "netherite_ingot", "netherite_sword", "netherite_pickaxe", "netherite_axe",
    "netherite_helmet", "netherite_chestplate", "netherite_leggings", "netherite_boots",
    "iron_ingot", "iron_sword", "iron_pickaxe", "iron_axe", "iron_shovel",
    "iron_helmet", "iron_chestplate", "iron_leggings", "iron_boots",
    "gold_ingot", "golden_sword", "golden_pickaxe", "golden_axe",
    "golden_helmet", "golden_chestplate", "golden_leggings", "golden_boots",
    "stone", "cobblestone", "dirt", "grass_block", "oak_log", "oak_planks",
    "spruce_log", "birch_log", "jungle_log", "acacia_log", "dark_oak_log",
    "coal", "charcoal", "stick", "torch", "lantern", "campfire",
    "crafting_table", "furnace", "chest", "ender_chest", "shulker_box",
    "bed", "white_bed", "red_bed", "blue_bed", "green_bed",
    "apple", "golden_apple", "enchanted_golden_apple", "bread", "cooked_beef",
    "cooked_porkchop", "cooked_chicken", "cooked_mutton", "cooked_salmon",
    "bow", "arrow", "spectral_arrow", "tipped_arrow", "crossbow",
    "shield", "trident", "elytra", "totem_of_undying",
    "ender_pearl", "eye_of_ender", "blaze_rod", "blaze_powder",
    "nether_star", "beacon", "conduit",
    "enchanting_table", "anvil", "brewing_stand", "cauldron",
    "redstone", "redstone_torch", "redstone_block", "repeater", "comparator",
    "piston", "sticky_piston", "observer", "hopper", "dropper", "dispenser",
    "tnt", "flint_and_steel", "fire_charge",
    "bucket", "water_bucket", "lava_bucket", "milk_bucket",
    "saddle", "lead", "name_tag",
    "spawn_egg", "experience_bottle", "writable_book", "written_book",
    "map", "filled_map", "compass", "clock", "spyglass",
    "potion", "splash_potion", "lingering_potion",
    "emerald", "lapis_lazuli", "quartz", "amethyst_shard",
    "copper_ingot", "raw_copper", "raw_iron", "raw_gold",
    "obsidian", "crying_obsidian", "glowstone", "sea_lantern",
    "bone", "bone_meal", "string", "feather", "leather", "rabbit_hide",
    "slime_ball", "honey_bottle", "honeycomb",
    "wheat", "wheat_seeds", "beetroot_seeds", "melon_seeds", "pumpkin_seeds",
    "carrot", "potato", "beetroot", "melon_slice", "pumpkin",
    "sugar_cane", "bamboo", "cactus", "cocoa_beans",
    "oak_sapling", "spruce_sapling", "birch_sapling", "jungle_sapling",
    "flower_pot", "painting", "item_frame", "glow_item_frame",
    "armor_stand", "end_crystal",
    "firework_rocket", "firework_star",
    "music_disc_13", "music_disc_cat", "music_disc_blocks", "music_disc_chirp",
    "command_block", "chain_command_block", "repeating_command_block",
    "structure_block", "jigsaw", "barrier", "light",
    "dragon_egg", "dragon_breath", "end_rod",
    "shulker_shell", "phantom_membrane", "turtle_egg", "scute",
    "heart_of_the_sea", "nautilus_shell", "prismarine_shard", "prismarine_crystals",
]

# Gamemodes disponibles
GAMEMODES = ["survival", "creative", "adventure", "spectator"]

# Types de météo
WEATHER_TYPES = ["clear", "rain", "thunder"]

# Niveaux de permission
class PermissionLevel:
    """Niveaux de permission pour les commandes RCON."""
    USER = 0        # Commandes basiques (aucune par défaut)
    MODERATOR = 1   # kick, say
    ADMIN = 2       # give, tp, gamemode, weather, time
    OWNER = 3       # execute (commande libre)


class RCONCog(commands.Cog, name="RCON"):
    """Cog pour les commandes RCON du serveur Minecraft."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rcon_client = None
        logger.info("Cog RCON initialisé")

    async def cog_load(self):
        """Appelé quand le cog est chargé."""
        # Récupérer le client RCON depuis le bot si disponible
        self.rcon_client = getattr(self.bot, 'rcon_client', None)
        if self.rcon_client:
            logger.info("Client RCON connecté au cog")
        else:
            logger.warning("Aucun client RCON disponible - les commandes ne fonctionneront pas")

    async def cog_unload(self):
        """Appelé quand le cog est déchargé."""
        logger.info("Cog RCON déchargé")

    # -------------------------------------------------------------------------
    # Méthodes utilitaires
    # -------------------------------------------------------------------------

    async def get_online_players(self) -> List[str]:
        """Récupère la liste des joueurs en ligne via RCON."""
        if not self.rcon_client:
            return []

        try:
            response = await self.rcon_client.send_command("list")
            # Format typique: "There are X of Y players online: player1, player2, ..."
            if ":" in response:
                players_part = response.split(":")[-1].strip()
                if players_part:
                    return [p.strip() for p in players_part.split(",") if p.strip()]
            return []
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des joueurs: {e}")
            return []

    async def execute_rcon(self, command: str) -> str:
        """Exécute une commande RCON et retourne la réponse."""
        if not self.rcon_client:
            raise RuntimeError("Client RCON non disponible")

        try:
            response = await self.rcon_client.send_command(command)
            return response if response else "Commande exécutée (pas de réponse)"
        except Exception as e:
            logger.error(f"Erreur RCON: {e}")
            raise

    def check_permission(self, user: discord.Member, required_level: int) -> bool:
        """Vérifie si l'utilisateur a le niveau de permission requis."""
        # Les administrateurs du serveur Discord ont toujours accès
        if user.guild_permissions.administrator:
            return True

        # Vérification basée sur les rôles
        user_level = PermissionLevel.USER

        role_names = [role.name.lower() for role in user.roles]

        if any(name in ["owner", "propriétaire", "fondateur"] for name in role_names):
            user_level = PermissionLevel.OWNER
        elif any(name in ["admin", "administrateur", "administrator"] for name in role_names):
            user_level = PermissionLevel.ADMIN
        elif any(name in ["mod", "moderator", "modérateur", "staff"] for name in role_names):
            user_level = PermissionLevel.MODERATOR

        return user_level >= required_level

    def create_response_embed(
        self,
        title: str,
        command: str,
        response: str,
        user: discord.Member,
        success: bool = True
    ) -> discord.Embed:
        """Crée un embed de réponse pour une commande RCON."""
        color = discord.Color.green() if success else discord.Color.red()

        embed = discord.Embed(
            title=f"{'✅' if success else '❌'} {title}",
            color=color,
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="Commande",
            value=f"```{command}```",
            inline=False
        )

        # Tronquer la réponse si elle est trop longue
        if len(response) > 1000:
            response = response[:997] + "..."

        embed.add_field(
            name="Réponse",
            value=f"```{response}```",
            inline=False
        )

        embed.set_footer(
            text=f"Exécuté par {user.display_name}",
            icon_url=user.display_avatar.url if user.display_avatar else None
        )

        return embed

    def log_command(
        self,
        user: discord.Member,
        command: str,
        response: str,
        success: bool
    ):
        """Log une commande RCON exécutée."""
        status = "SUCCESS" if success else "FAILED"
        logger.info(
            f"[RCON {status}] User: {user} ({user.id}) | "
            f"Guild: {user.guild.name} ({user.guild.id}) | "
            f"Command: {command} | Response: {response[:100]}..."
        )

    # -------------------------------------------------------------------------
    # Autocomplete handlers
    # -------------------------------------------------------------------------

    async def player_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete pour les noms de joueurs en ligne."""
        players = await self.get_online_players()

        if current:
            players = [p for p in players if current.lower() in p.lower()]

        return [
            app_commands.Choice(name=player, value=player)
            for player in players[:25]  # Discord limite à 25 choix
        ]

    async def item_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete pour les items Minecraft."""
        if current:
            filtered = [
                item for item in MINECRAFT_ITEMS
                if current.lower() in item.lower()
            ]
        else:
            filtered = MINECRAFT_ITEMS[:25]

        return [
            app_commands.Choice(name=item.replace("_", " ").title(), value=item)
            for item in filtered[:25]
        ]

    async def gamemode_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete pour les gamemodes."""
        if current:
            filtered = [gm for gm in GAMEMODES if current.lower() in gm.lower()]
        else:
            filtered = GAMEMODES

        return [
            app_commands.Choice(name=gm.capitalize(), value=gm)
            for gm in filtered
        ]

    async def weather_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete pour les types de météo."""
        if current:
            filtered = [w for w in WEATHER_TYPES if current.lower() in w.lower()]
        else:
            filtered = WEATHER_TYPES

        return [
            app_commands.Choice(name=w.capitalize(), value=w)
            for w in filtered
        ]

    # -------------------------------------------------------------------------
    # Groupe de commandes RCON
    # -------------------------------------------------------------------------

    rcon_group = app_commands.Group(
        name="rcon",
        description="Commandes RCON pour le serveur Minecraft"
    )

    @rcon_group.command(name="execute", description="Exécuter une commande RCON libre (Admin)")
    @app_commands.describe(command="La commande Minecraft à exécuter")
    async def rcon_execute(self, interaction: discord.Interaction, command: str):
        """Exécute une commande RCON arbitraire."""
        # Vérification des permissions (Owner uniquement)
        if not self.check_permission(interaction.user, PermissionLevel.OWNER):
            await interaction.response.send_message(
                "❌ Permission refusée. Cette commande nécessite le niveau Owner.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # Valider la commande
        is_valid, error = validate_rcon_command(command)
        if not is_valid:
            await interaction.followup.send(f"❌ Commande invalide: {error}", ephemeral=True)
            return

        # Avertir pour les commandes dangereuses
        if is_dangerous_command(command):
            await interaction.followup.send(
                "⚠️ Cette commande est potentiellement dangereuse. Exécution avec précaution.",
                ephemeral=True
            )

        # Sanitize
        command = sanitize_rcon_input(command, max_length=1000)

        try:
            response = await self.execute_rcon(command)
            embed = self.create_response_embed(
                "Commande RCON Exécutée",
                command,
                response,
                interaction.user,
                success=True
            )
            self.log_command(interaction.user, command, response, True)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = self.create_response_embed(
                "Erreur RCON",
                command,
                str(e),
                interaction.user,
                success=False
            )
            self.log_command(interaction.user, command, str(e), False)
            await interaction.followup.send(embed=embed)

    @rcon_group.command(name="give", description="Donner un item à un joueur")
    @app_commands.describe(
        player="Le joueur qui recevra l'item",
        item="L'item à donner",
        amount="Quantité (défaut: 1)"
    )
    @app_commands.autocomplete(player=player_autocomplete, item=item_autocomplete)
    async def rcon_give(
        self,
        interaction: discord.Interaction,
        player: str,
        item: str,
        amount: Optional[int] = 1
    ):
        """Donne un item à un joueur."""
        if not self.check_permission(interaction.user, PermissionLevel.ADMIN):
            await interaction.response.send_message(
                "❌ Permission refusée. Cette commande nécessite le niveau Admin.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # Validation du nom de joueur
        if not validate_minecraft_username(player):
            await interaction.followup.send(
                "❌ Nom de joueur invalide. Utilisez 3-16 caractères (lettres, chiffres, _)",
                ephemeral=True
            )
            return

        # Sanitize l'item
        item = sanitize_rcon_input(item, max_length=64)

        # Validation de la quantité
        if amount < 1:
            amount = 1
        elif amount > 64 * 27 * 4:  # Limite raisonnable
            amount = 64

        command = f"give {player} minecraft:{item} {amount}"

        try:
            response = await self.execute_rcon(command)
            embed = self.create_response_embed(
                "Item Donné",
                command,
                response,
                interaction.user,
                success=True
            )
            self.log_command(interaction.user, command, response, True)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = self.create_response_embed(
                "Erreur Give",
                command,
                str(e),
                interaction.user,
                success=False
            )
            self.log_command(interaction.user, command, str(e), False)
            await interaction.followup.send(embed=embed)

    @rcon_group.command(name="tp", description="Téléporter un joueur")
    @app_commands.describe(
        player="Le joueur à téléporter",
        destination="Destination (joueur ou coordonnées x y z)"
    )
    @app_commands.autocomplete(player=player_autocomplete)
    async def rcon_tp(
        self,
        interaction: discord.Interaction,
        player: str,
        destination: str
    ):
        """Téléporte un joueur vers une destination."""
        if not self.check_permission(interaction.user, PermissionLevel.ADMIN):
            await interaction.response.send_message(
                "❌ Permission refusée. Cette commande nécessite le niveau Admin.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # Validation du nom de joueur
        if not validate_minecraft_username(player):
            await interaction.followup.send(
                "❌ Nom de joueur invalide. Utilisez 3-16 caractères (lettres, chiffres, _)",
                ephemeral=True
            )
            return

        # Sanitize la destination
        destination = sanitize_rcon_input(destination, max_length=128)

        command = f"tp {player} {destination}"

        try:
            response = await self.execute_rcon(command)
            embed = self.create_response_embed(
                "Téléportation Effectuée",
                command,
                response,
                interaction.user,
                success=True
            )
            self.log_command(interaction.user, command, response, True)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = self.create_response_embed(
                "Erreur Téléportation",
                command,
                str(e),
                interaction.user,
                success=False
            )
            self.log_command(interaction.user, command, str(e), False)
            await interaction.followup.send(embed=embed)

    @rcon_group.command(name="gamemode", description="Changer le gamemode d'un joueur")
    @app_commands.describe(
        player="Le joueur dont changer le gamemode",
        mode="Le nouveau gamemode"
    )
    @app_commands.autocomplete(player=player_autocomplete, mode=gamemode_autocomplete)
    async def rcon_gamemode(
        self,
        interaction: discord.Interaction,
        player: str,
        mode: str
    ):
        """Change le gamemode d'un joueur."""
        if not self.check_permission(interaction.user, PermissionLevel.ADMIN):
            await interaction.response.send_message(
                "❌ Permission refusée. Cette commande nécessite le niveau Admin.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # Validation du nom de joueur
        if not validate_minecraft_username(player):
            await interaction.followup.send(
                "❌ Nom de joueur invalide. Utilisez 3-16 caractères (lettres, chiffres, _)",
                ephemeral=True
            )
            return

        # Validation du gamemode
        if mode.lower() not in GAMEMODES:
            await interaction.followup.send(
                f"❌ Gamemode invalide. Choix possibles: {', '.join(GAMEMODES)}",
                ephemeral=True
            )
            return

        command = f"gamemode {mode} {player}"

        try:
            response = await self.execute_rcon(command)
            embed = self.create_response_embed(
                "Gamemode Changé",
                command,
                response,
                interaction.user,
                success=True
            )
            self.log_command(interaction.user, command, response, True)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = self.create_response_embed(
                "Erreur Gamemode",
                command,
                str(e),
                interaction.user,
                success=False
            )
            self.log_command(interaction.user, command, str(e), False)
            await interaction.followup.send(embed=embed)

    @rcon_group.command(name="weather", description="Changer la météo du serveur")
    @app_commands.describe(
        weather_type="Type de météo",
        duration="Durée en secondes (optionnel)"
    )
    @app_commands.autocomplete(weather_type=weather_autocomplete)
    async def rcon_weather(
        self,
        interaction: discord.Interaction,
        weather_type: str,
        duration: Optional[int] = None
    ):
        """Change la météo du serveur."""
        if not self.check_permission(interaction.user, PermissionLevel.ADMIN):
            await interaction.response.send_message(
                "❌ Permission refusée. Cette commande nécessite le niveau Admin.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # Validation du type de météo
        if weather_type.lower() not in WEATHER_TYPES:
            await interaction.followup.send(
                f"❌ Type de météo invalide. Choix possibles: {', '.join(WEATHER_TYPES)}",
                ephemeral=True
            )
            return

        if duration and duration > 0:
            command = f"weather {weather_type} {duration}"
        else:
            command = f"weather {weather_type}"

        try:
            response = await self.execute_rcon(command)
            embed = self.create_response_embed(
                "Météo Changée",
                command,
                response,
                interaction.user,
                success=True
            )
            self.log_command(interaction.user, command, response, True)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = self.create_response_embed(
                "Erreur Météo",
                command,
                str(e),
                interaction.user,
                success=False
            )
            self.log_command(interaction.user, command, str(e), False)
            await interaction.followup.send(embed=embed)

    @rcon_group.command(name="time", description="Changer le temps du serveur")
    @app_commands.describe(
        action="Action (set ou add)",
        value="Valeur (nombre ou day/night/noon/midnight)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Définir", value="set"),
        app_commands.Choice(name="Ajouter", value="add")
    ])
    async def rcon_time(
        self,
        interaction: discord.Interaction,
        action: str,
        value: str
    ):
        """Change le temps du serveur."""
        if not self.check_permission(interaction.user, PermissionLevel.ADMIN):
            await interaction.response.send_message(
                "❌ Permission refusée. Cette commande nécessite le niveau Admin.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        command = f"time {action} {value}"

        try:
            response = await self.execute_rcon(command)
            embed = self.create_response_embed(
                "Temps Modifié",
                command,
                response,
                interaction.user,
                success=True
            )
            self.log_command(interaction.user, command, response, True)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = self.create_response_embed(
                "Erreur Time",
                command,
                str(e),
                interaction.user,
                success=False
            )
            self.log_command(interaction.user, command, str(e), False)
            await interaction.followup.send(embed=embed)

    @rcon_group.command(name="say", description="Envoyer un message sur le serveur")
    @app_commands.describe(message="Le message à envoyer")
    async def rcon_say(self, interaction: discord.Interaction, message: str):
        """Envoie un message à tous les joueurs sur le serveur."""
        if not self.check_permission(interaction.user, PermissionLevel.MODERATOR):
            await interaction.response.send_message(
                "❌ Permission refusée. Cette commande nécessite le niveau Modérateur.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # Sanitize le message
        message = sanitize_rcon_input(message, max_length=256)
        if not message:
            await interaction.followup.send("❌ Le message ne peut pas être vide.", ephemeral=True)
            return

        command = f"say [{interaction.user.display_name}] {message}"

        try:
            response = await self.execute_rcon(command)
            embed = self.create_response_embed(
                "Message Envoyé",
                command,
                response,
                interaction.user,
                success=True
            )
            self.log_command(interaction.user, command, response, True)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = self.create_response_embed(
                "Erreur Say",
                command,
                str(e),
                interaction.user,
                success=False
            )
            self.log_command(interaction.user, command, str(e), False)
            await interaction.followup.send(embed=embed)

    @rcon_group.command(name="kick", description="Expulser un joueur du serveur")
    @app_commands.describe(
        player="Le joueur à expulser",
        reason="Raison de l'expulsion (optionnel)"
    )
    @app_commands.autocomplete(player=player_autocomplete)
    async def rcon_kick(
        self,
        interaction: discord.Interaction,
        player: str,
        reason: Optional[str] = None
    ):
        """Expulse un joueur du serveur."""
        if not self.check_permission(interaction.user, PermissionLevel.MODERATOR):
            await interaction.response.send_message(
                "❌ Permission refusée. Cette commande nécessite le niveau Modérateur.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # Validation du nom de joueur
        if not validate_minecraft_username(player):
            await interaction.followup.send(
                "❌ Nom de joueur invalide. Utilisez 3-16 caractères (lettres, chiffres, _)",
                ephemeral=True
            )
            return

        # Sanitize la raison si presente
        if reason:
            reason = sanitize_rcon_input(reason, max_length=256)

        if reason:
            command = f"kick {player} {reason}"
        else:
            command = f"kick {player}"

        try:
            response = await self.execute_rcon(command)
            embed = self.create_response_embed(
                "Joueur Expulsé",
                command,
                response,
                interaction.user,
                success=True
            )
            self.log_command(interaction.user, command, response, True)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = self.create_response_embed(
                "Erreur Kick",
                command,
                str(e),
                interaction.user,
                success=False
            )
            self.log_command(interaction.user, command, str(e), False)
            await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    """Fonction de setup pour charger le cog."""
    await bot.add_cog(RCONCog(bot))
    logger.info("Cog RCON chargé avec succès")
