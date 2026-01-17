"""
Cog de gestion des joueurs Minecraft.
Commandes pour la gestion des joueurs, whitelist, bans et OPs.
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional, List
from datetime import datetime, timedelta
import aiohttp
import asyncio
import re

from src.utils.validators import validate_minecraft_username, sanitize_rcon_input


class PlayersPaginator(discord.ui.View):
    """Vue de pagination pour les listes longues."""

    def __init__(self, embeds: List[discord.Embed], author_id: int, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.author_id = author_id
        self.current_page = 0
        self.total_pages = len(embeds)
        self._update_buttons()

    def _update_buttons(self):
        """Met a jour l'etat des boutons."""
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page >= self.total_pages - 1
        self.last_page.disabled = self.current_page >= self.total_pages - 1

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
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Page precedente."""
        self.current_page = max(0, self.current_page - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Page suivante."""
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Derniere page."""
        self.current_page = self.total_pages - 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


class AutoRefreshPlayersView(discord.ui.View):
    """Vue avec auto-refresh pour la liste des joueurs."""

    def __init__(self, cog: 'PlayersCog', timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.message: Optional[discord.Message] = None
        self.is_refreshing = True

    async def on_timeout(self):
        """Arrete le refresh a l'expiration."""
        self.is_refreshing = False
        if self.message:
            for item in self.children:
                item.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

    @discord.ui.button(label="Actualiser", style=discord.ButtonStyle.primary, emoji="\U0001F504")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Actualise manuellement la liste."""
        await interaction.response.defer()
        embed = await self.cog.create_players_list_embed()
        await interaction.edit_original_response(embed=embed)

    @discord.ui.button(label="Arreter", style=discord.ButtonStyle.danger, emoji="\u23F9")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Arrete l'auto-refresh."""
        self.is_refreshing = False
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)


class PlayersCog(commands.Cog):
    """Cog pour la gestion des joueurs Minecraft."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self.uuid_cache: dict = {}  # Cache UUID pour les joueurs
        self.auto_refresh_views: List[AutoRefreshPlayersView] = []
        self.auto_refresh_task.start()

    async def cog_load(self):
        """Initialise la session HTTP au chargement."""
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        """Ferme la session HTTP au dechargement."""
        self.auto_refresh_task.cancel()
        if self.session:
            await self.session.close()

    @tasks.loop(seconds=30)
    async def auto_refresh_task(self):
        """Tache de refresh automatique des listes de joueurs."""
        for view in self.auto_refresh_views[:]:
            if not view.is_refreshing or view.message is None:
                self.auto_refresh_views.remove(view)
                continue
            try:
                embed = await self.create_players_list_embed()
                await view.message.edit(embed=embed)
            except discord.NotFound:
                self.auto_refresh_views.remove(view)
            except Exception:
                pass

    @auto_refresh_task.before_loop
    async def before_auto_refresh(self):
        """Attend que le bot soit pret."""
        await self.bot.wait_until_ready()

    # ==================== Utilitaires ====================

    async def get_rcon(self):
        """Recupere le client RCON depuis le bot."""
        if hasattr(self.bot, 'rcon') and self.bot.rcon:
            return self.bot.rcon
        return None

    async def execute_command(self, command: str) -> Optional[str]:
        """Execute une commande RCON."""
        rcon = await self.get_rcon()
        if rcon:
            try:
                return await rcon.command(command)
            except Exception as e:
                return f"Erreur RCON: {e}"
        return None

    async def get_player_uuid(self, player_name: str) -> Optional[str]:
        """Recupere l'UUID d'un joueur via l'API Mojang."""
        if player_name.lower() in self.uuid_cache:
            return self.uuid_cache[player_name.lower()]

        if not self.session:
            return None

        try:
            url = f"https://api.mojang.com/users/profiles/minecraft/{player_name}"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    uuid = data.get('id')
                    if uuid:
                        # Formater l'UUID avec tirets
                        formatted_uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
                        self.uuid_cache[player_name.lower()] = formatted_uuid
                        return formatted_uuid
        except Exception:
            pass
        return None

    def get_avatar_url(self, uuid: str, size: int = 100) -> str:
        """Genere l'URL de l'avatar Minecraft via Crafatar."""
        clean_uuid = uuid.replace('-', '')
        return f"https://crafatar.com/avatars/{clean_uuid}?size={size}&overlay"

    def get_body_url(self, uuid: str, size: int = 100) -> str:
        """Genere l'URL du corps complet via Crafatar."""
        clean_uuid = uuid.replace('-', '')
        return f"https://crafatar.com/renders/body/{clean_uuid}?size={size}&overlay"

    def get_head_url(self, uuid: str, size: int = 100) -> str:
        """Genere l'URL de la tete 3D via Crafatar."""
        clean_uuid = uuid.replace('-', '')
        return f"https://crafatar.com/renders/head/{clean_uuid}?size={size}&overlay"

    async def log_action(self, action: str, target: str, moderator: discord.User,
                         reason: Optional[str] = None, duration: Optional[str] = None):
        """Log une action dans la base de donnees."""
        if hasattr(self.bot, 'db') and self.bot.db:
            try:
                await self.bot.db.execute(
                    """
                    INSERT INTO player_logs (action, target, moderator_id, moderator_name, reason, duration, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (action, target, moderator.id, str(moderator), reason, duration, datetime.utcnow().isoformat())
                )
                await self.bot.db.commit()
            except Exception:
                pass

    async def get_online_players(self) -> List[str]:
        """Recupere la liste des joueurs en ligne."""
        response = await self.execute_command("list")
        if response:
            # Parse la reponse "There are X of a max of Y players online: player1, player2"
            match = re.search(r':\s*(.+)$', response)
            if match:
                players_str = match.group(1).strip()
                if players_str:
                    return [p.strip() for p in players_str.split(',') if p.strip()]
        return []

    async def player_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete pour les noms de joueurs en ligne."""
        players = await self.get_online_players()
        return [
            app_commands.Choice(name=player, value=player)
            for player in players
            if current.lower() in player.lower()
        ][:25]

    async def create_players_list_embed(self) -> discord.Embed:
        """Cree un embed de liste des joueurs en ligne."""
        players = await self.get_online_players()

        embed = discord.Embed(
            title="\U0001F3AE Joueurs en ligne",
            color=discord.Color.green() if players else discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        if players:
            embed.description = f"**{len(players)}** joueur(s) connecte(s)"

            # Affiche les joueurs avec leur avatar
            players_text = ""
            for player in players[:20]:  # Limite a 20 pour l'embed
                players_text += f"\U0001F7E2 **{player}**\n"

            if len(players) > 20:
                players_text += f"\n*... et {len(players) - 20} autres*"

            embed.add_field(name="Joueurs", value=players_text, inline=False)

            # Ajoute l'avatar du premier joueur comme thumbnail
            if players:
                uuid = await self.get_player_uuid(players[0])
                if uuid:
                    embed.set_thumbnail(url=self.get_avatar_url(uuid))
        else:
            embed.description = "Aucun joueur en ligne"
            embed.set_thumbnail(url="https://crafatar.com/avatars/steve?size=100")

        embed.set_footer(text="Auto-refresh toutes les 30s")
        return embed

    def create_paginated_embeds(self, title: str, items: List[str],
                                 items_per_page: int = 10, color: discord.Color = None) -> List[discord.Embed]:
        """Cree des embeds pagines pour une liste."""
        if not items:
            embed = discord.Embed(
                title=title,
                description="Aucun element a afficher",
                color=color or discord.Color.blue()
            )
            return [embed]

        embeds = []
        total_pages = (len(items) + items_per_page - 1) // items_per_page

        for page in range(total_pages):
            start = page * items_per_page
            end = start + items_per_page
            page_items = items[start:end]

            embed = discord.Embed(
                title=title,
                description="\n".join(page_items),
                color=color or discord.Color.blue()
            )
            embed.set_footer(text=f"Page {page + 1}/{total_pages} | Total: {len(items)}")
            embeds.append(embed)

        return embeds

    # ==================== Groupe /players ====================

    players_group = app_commands.Group(name="players", description="Gestion des joueurs")

    @players_group.command(name="list", description="Liste des joueurs en ligne avec auto-refresh")
    async def players_list(self, interaction: discord.Interaction):
        """Affiche la liste des joueurs en ligne."""
        await interaction.response.defer()

        embed = await self.create_players_list_embed()
        view = AutoRefreshPlayersView(self)

        message = await interaction.followup.send(embed=embed, view=view)
        view.message = message
        self.auto_refresh_views.append(view)

        await self.log_action("players_list", "all", interaction.user)

    @players_group.command(name="info", description="Informations detaillees sur un joueur")
    @app_commands.describe(player="Nom du joueur")
    @app_commands.autocomplete(player=player_autocomplete)
    async def players_info(self, interaction: discord.Interaction, player: str):
        """Affiche les informations detaillees d'un joueur."""
        await interaction.response.defer()

        # Validation du nom de joueur
        if not validate_minecraft_username(player):
            await interaction.followup.send(
                "❌ Nom de joueur invalide. Utilisez 3-16 caractères (lettres, chiffres, _)",
                ephemeral=True
            )
            return

        uuid = await self.get_player_uuid(player)
        online_players = await self.get_online_players()
        is_online = player in online_players

        embed = discord.Embed(
            title=f"\U0001F464 Informations: {player}",
            color=discord.Color.green() if is_online else discord.Color.gray(),
            timestamp=datetime.utcnow()
        )

        # Statut
        status = "\U0001F7E2 En ligne" if is_online else "\U0001F534 Hors ligne"
        embed.add_field(name="Statut", value=status, inline=True)

        # UUID
        if uuid:
            embed.add_field(name="UUID", value=f"`{uuid}`", inline=False)
            embed.set_thumbnail(url=self.get_head_url(uuid, 150))
            embed.set_image(url=self.get_body_url(uuid, 200))
        else:
            embed.add_field(name="UUID", value="*Non trouve*", inline=False)

        # Infos supplementaires depuis la DB si disponible
        if hasattr(self.bot, 'db') and self.bot.db:
            try:
                cursor = await self.bot.db.execute(
                    "SELECT * FROM player_stats WHERE player_name = ?",
                    (player,)
                )
                stats = await cursor.fetchone()
                if stats:
                    embed.add_field(name="Premiere connexion", value=stats['first_join'] or "Inconnue", inline=True)
                    embed.add_field(name="Derniere connexion", value=stats['last_join'] or "Inconnue", inline=True)
                    embed.add_field(name="Temps de jeu", value=stats.get('playtime', 'Inconnu'), inline=True)
            except Exception:
                pass

        await interaction.followup.send(embed=embed)
        await self.log_action("players_info", player, interaction.user)

    @players_group.command(name="history", description="Historique des connexions d'un joueur")
    @app_commands.describe(player="Nom du joueur")
    @app_commands.autocomplete(player=player_autocomplete)
    async def players_history(self, interaction: discord.Interaction, player: str):
        """Affiche l'historique des connexions d'un joueur."""
        await interaction.response.defer()

        # Validation du nom de joueur
        if not validate_minecraft_username(player):
            await interaction.followup.send(
                "❌ Nom de joueur invalide. Utilisez 3-16 caractères (lettres, chiffres, _)",
                ephemeral=True
            )
            return

        uuid = await self.get_player_uuid(player)
        history_items = []

        # Recupere l'historique depuis la DB
        if hasattr(self.bot, 'db') and self.bot.db:
            try:
                cursor = await self.bot.db.execute(
                    """
                    SELECT event_type, timestamp
                    FROM connection_history
                    WHERE player_name = ?
                    ORDER BY timestamp DESC
                    LIMIT 50
                    """,
                    (player,)
                )
                rows = await cursor.fetchall()
                for row in rows:
                    event_icon = "\U0001F7E2" if row['event_type'] == 'join' else "\U0001F534"
                    event_text = "Connexion" if row['event_type'] == 'join' else "Deconnexion"
                    history_items.append(f"{event_icon} **{event_text}** - {row['timestamp']}")
            except Exception:
                pass

        if not history_items:
            history_items = ["Aucun historique disponible"]

        embeds = self.create_paginated_embeds(
            f"\U0001F4DC Historique: {player}",
            history_items,
            items_per_page=10,
            color=discord.Color.blue()
        )

        # Ajoute l'avatar si disponible
        if uuid:
            for embed in embeds:
                embed.set_thumbnail(url=self.get_avatar_url(uuid))

        if len(embeds) > 1:
            view = PlayersPaginator(embeds, interaction.user.id)
            await interaction.followup.send(embed=embeds[0], view=view)
        else:
            await interaction.followup.send(embed=embeds[0])

        await self.log_action("players_history", player, interaction.user)

    # ==================== Groupe /whitelist ====================

    whitelist_group = app_commands.Group(name="whitelist", description="Gestion de la whitelist")

    @whitelist_group.command(name="add", description="Ajouter un joueur a la whitelist")
    @app_commands.describe(player="Nom du joueur a ajouter")
    @app_commands.checks.has_permissions(administrator=True)
    async def whitelist_add(self, interaction: discord.Interaction, player: str):
        """Ajoute un joueur a la whitelist."""
        await interaction.response.defer()

        # Validation du nom de joueur
        if not validate_minecraft_username(player):
            await interaction.followup.send(
                "❌ Nom de joueur invalide. Utilisez 3-16 caractères (lettres, chiffres, _)",
                ephemeral=True
            )
            return

        response = await self.execute_command(f"whitelist add {player}")

        embed = discord.Embed(
            title="\U0001F4DD Whitelist",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        uuid = await self.get_player_uuid(player)
        if uuid:
            embed.set_thumbnail(url=self.get_avatar_url(uuid))

        if response and "Added" in response:
            embed.description = f"\u2705 **{player}** a ete ajoute a la whitelist"
        elif response and "already" in response.lower():
            embed.description = f"\u26A0\uFE0F **{player}** est deja dans la whitelist"
            embed.color = discord.Color.yellow()
        else:
            embed.description = f"\u274C Erreur: {response or 'Pas de reponse du serveur'}"
            embed.color = discord.Color.red()

        await interaction.followup.send(embed=embed)
        await self.log_action("whitelist_add", player, interaction.user)

    @whitelist_group.command(name="remove", description="Retirer un joueur de la whitelist")
    @app_commands.describe(player="Nom du joueur a retirer")
    @app_commands.checks.has_permissions(administrator=True)
    async def whitelist_remove(self, interaction: discord.Interaction, player: str):
        """Retire un joueur de la whitelist."""
        await interaction.response.defer()

        # Validation du nom de joueur
        if not validate_minecraft_username(player):
            await interaction.followup.send(
                "❌ Nom de joueur invalide. Utilisez 3-16 caractères (lettres, chiffres, _)",
                ephemeral=True
            )
            return

        response = await self.execute_command(f"whitelist remove {player}")

        embed = discord.Embed(
            title="\U0001F4DD Whitelist",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        uuid = await self.get_player_uuid(player)
        if uuid:
            embed.set_thumbnail(url=self.get_avatar_url(uuid))

        if response and "Removed" in response:
            embed.description = f"\u2705 **{player}** a ete retire de la whitelist"
        else:
            embed.description = f"\u274C Erreur: {response or 'Pas de reponse du serveur'}"
            embed.color = discord.Color.red()

        await interaction.followup.send(embed=embed)
        await self.log_action("whitelist_remove", player, interaction.user)

    @whitelist_group.command(name="list", description="Afficher la whitelist")
    async def whitelist_list(self, interaction: discord.Interaction):
        """Affiche la whitelist."""
        await interaction.response.defer()

        response = await self.execute_command("whitelist list")

        players = []
        if response:
            # Parse "There are X whitelisted players: player1, player2"
            match = re.search(r':\s*(.+)$', response)
            if match:
                players_str = match.group(1).strip()
                if players_str:
                    players = [f"\u2705 **{p.strip()}**" for p in players_str.split(',') if p.strip()]

        embeds = self.create_paginated_embeds(
            "\U0001F4CB Whitelist",
            players if players else ["Aucun joueur dans la whitelist"],
            items_per_page=15,
            color=discord.Color.green()
        )

        if len(embeds) > 1:
            view = PlayersPaginator(embeds, interaction.user.id)
            await interaction.followup.send(embed=embeds[0], view=view)
        else:
            await interaction.followup.send(embed=embeds[0])

        await self.log_action("whitelist_list", "all", interaction.user)

    # ==================== Commandes de ban ====================

    @app_commands.command(name="ban", description="Bannir un joueur")
    @app_commands.describe(
        player="Nom du joueur a bannir",
        reason="Raison du bannissement",
        duration="Duree du ban (ex: 1d, 1w, 1m, perm)"
    )
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.autocomplete(player=player_autocomplete)
    async def ban_player(self, interaction: discord.Interaction, player: str,
                         reason: Optional[str] = None, duration: Optional[str] = None):
        """Bannit un joueur du serveur."""
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

        # Construit la commande de ban
        ban_cmd = f"ban {player}"
        if reason:
            ban_cmd += f" {reason}"

        response = await self.execute_command(ban_cmd)

        embed = discord.Embed(
            title="\U0001F6AB Bannissement",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        uuid = await self.get_player_uuid(player)
        if uuid:
            embed.set_thumbnail(url=self.get_avatar_url(uuid))

        if response and ("Banned" in response or "banned" in response.lower()):
            embed.description = f"\u2705 **{player}** a ete banni"
            embed.add_field(name="Raison", value=reason or "Non specifiee", inline=True)
            embed.add_field(name="Duree", value=duration or "Permanent", inline=True)
            embed.add_field(name="Moderateur", value=interaction.user.mention, inline=True)

            # Enregistre le ban dans la DB avec duree si specifie
            if hasattr(self.bot, 'db') and self.bot.db:
                try:
                    expires_at = None
                    if duration and duration.lower() != "perm":
                        # Parse la duree
                        duration_match = re.match(r'(\d+)([dwmh])', duration.lower())
                        if duration_match:
                            amount = int(duration_match.group(1))
                            unit = duration_match.group(2)
                            if unit == 'h':
                                expires_at = datetime.utcnow() + timedelta(hours=amount)
                            elif unit == 'd':
                                expires_at = datetime.utcnow() + timedelta(days=amount)
                            elif unit == 'w':
                                expires_at = datetime.utcnow() + timedelta(weeks=amount)
                            elif unit == 'm':
                                expires_at = datetime.utcnow() + timedelta(days=amount*30)

                    await self.bot.db.execute(
                        """
                        INSERT INTO bans (player_name, reason, moderator_id, banned_at, expires_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (player, reason, interaction.user.id, datetime.utcnow().isoformat(),
                         expires_at.isoformat() if expires_at else None)
                    )
                    await self.bot.db.commit()
                except Exception:
                    pass
        else:
            embed.description = f"\u274C Erreur: {response or 'Pas de reponse du serveur'}"

        await interaction.followup.send(embed=embed)
        await self.log_action("ban", player, interaction.user, reason, duration)

    @app_commands.command(name="unban", description="Debannir un joueur")
    @app_commands.describe(player="Nom du joueur a debannir")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban_player(self, interaction: discord.Interaction, player: str):
        """Debannit un joueur."""
        await interaction.response.defer()

        # Validation du nom de joueur
        if not validate_minecraft_username(player):
            await interaction.followup.send(
                "❌ Nom de joueur invalide. Utilisez 3-16 caractères (lettres, chiffres, _)",
                ephemeral=True
            )
            return

        response = await self.execute_command(f"pardon {player}")

        embed = discord.Embed(
            title="\u2705 Debannissement",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        uuid = await self.get_player_uuid(player)
        if uuid:
            embed.set_thumbnail(url=self.get_avatar_url(uuid))

        if response and ("Unbanned" in response or "pardoned" in response.lower() or not response.startswith("Could not")):
            embed.description = f"**{player}** a ete debanni"

            # Met a jour la DB
            if hasattr(self.bot, 'db') and self.bot.db:
                try:
                    await self.bot.db.execute(
                        "DELETE FROM bans WHERE player_name = ?",
                        (player,)
                    )
                    await self.bot.db.commit()
                except Exception:
                    pass
        else:
            embed.description = f"\u274C Erreur: {response or 'Pas de reponse du serveur'}"
            embed.color = discord.Color.red()

        await interaction.followup.send(embed=embed)
        await self.log_action("unban", player, interaction.user)

    @app_commands.command(name="banlist", description="Liste des joueurs bannis")
    async def banlist(self, interaction: discord.Interaction):
        """Affiche la liste des joueurs bannis."""
        await interaction.response.defer()

        response = await self.execute_command("banlist")

        players = []
        if response:
            # Parse "There are X bans: player1: reason, player2: reason"
            match = re.search(r':\s*(.+)$', response)
            if match:
                bans_str = match.group(1).strip()
                if bans_str and "There are no bans" not in response:
                    # Chaque ban peut avoir une raison
                    for ban in bans_str.split(','):
                        ban = ban.strip()
                        if ban:
                            players.append(f"\U0001F6AB **{ban}**")

        embeds = self.create_paginated_embeds(
            "\U0001F6AB Liste des bannis",
            players if players else ["Aucun joueur banni"],
            items_per_page=15,
            color=discord.Color.red()
        )

        if len(embeds) > 1:
            view = PlayersPaginator(embeds, interaction.user.id)
            await interaction.followup.send(embed=embeds[0], view=view)
        else:
            await interaction.followup.send(embed=embeds[0])

        await self.log_action("banlist", "all", interaction.user)

    # ==================== Commandes OP ====================

    @app_commands.command(name="op", description="Donner les droits operateur a un joueur")
    @app_commands.describe(player="Nom du joueur")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(player=player_autocomplete)
    async def op_player(self, interaction: discord.Interaction, player: str):
        """Donne les droits OP a un joueur."""
        await interaction.response.defer()

        # Validation du nom de joueur
        if not validate_minecraft_username(player):
            await interaction.followup.send(
                "❌ Nom de joueur invalide. Utilisez 3-16 caractères (lettres, chiffres, _)",
                ephemeral=True
            )
            return

        response = await self.execute_command(f"op {player}")

        embed = discord.Embed(
            title="\u2B50 Operateur",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        uuid = await self.get_player_uuid(player)
        if uuid:
            embed.set_thumbnail(url=self.get_avatar_url(uuid))

        if response and ("Made" in response or "opped" in response.lower()):
            embed.description = f"\u2705 **{player}** est maintenant operateur"
        elif response and "already" in response.lower():
            embed.description = f"\u26A0\uFE0F **{player}** est deja operateur"
            embed.color = discord.Color.yellow()
        else:
            embed.description = f"\u274C Erreur: {response or 'Pas de reponse du serveur'}"
            embed.color = discord.Color.red()

        await interaction.followup.send(embed=embed)
        await self.log_action("op", player, interaction.user)

    @app_commands.command(name="deop", description="Retirer les droits operateur a un joueur")
    @app_commands.describe(player="Nom du joueur")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(player=player_autocomplete)
    async def deop_player(self, interaction: discord.Interaction, player: str):
        """Retire les droits OP a un joueur."""
        await interaction.response.defer()

        # Validation du nom de joueur
        if not validate_minecraft_username(player):
            await interaction.followup.send(
                "❌ Nom de joueur invalide. Utilisez 3-16 caractères (lettres, chiffres, _)",
                ephemeral=True
            )
            return

        response = await self.execute_command(f"deop {player}")

        embed = discord.Embed(
            title="\u2B50 Operateur",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        uuid = await self.get_player_uuid(player)
        if uuid:
            embed.set_thumbnail(url=self.get_avatar_url(uuid))

        if response and ("Made" in response or "de-opped" in response.lower() or "no longer" in response.lower()):
            embed.description = f"\u2705 **{player}** n'est plus operateur"
        else:
            embed.description = f"\u274C Erreur: {response or 'Pas de reponse du serveur'}"
            embed.color = discord.Color.red()

        await interaction.followup.send(embed=embed)
        await self.log_action("deop", player, interaction.user)

    @app_commands.command(name="oplist", description="Liste des operateurs")
    async def oplist(self, interaction: discord.Interaction):
        """Affiche la liste des operateurs."""
        await interaction.response.defer()

        response = await self.execute_command("op list")

        # Alternative: lire ops.json si disponible
        players = []
        if response:
            # Parse la reponse
            match = re.search(r':\s*(.+)$', response)
            if match:
                ops_str = match.group(1).strip()
                if ops_str:
                    players = [f"\u2B50 **{op.strip()}**" for op in ops_str.split(',') if op.strip()]

        embeds = self.create_paginated_embeds(
            "\u2B50 Liste des Operateurs",
            players if players else ["Aucun operateur"],
            items_per_page=15,
            color=discord.Color.gold()
        )

        if len(embeds) > 1:
            view = PlayersPaginator(embeds, interaction.user.id)
            await interaction.followup.send(embed=embeds[0], view=view)
        else:
            await interaction.followup.send(embed=embeds[0])

        await self.log_action("oplist", "all", interaction.user)

    # ==================== Gestion des erreurs ====================

    @whitelist_add.error
    @whitelist_remove.error
    @op_player.error
    @deop_player.error
    async def admin_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Gere les erreurs de permissions pour les commandes admin."""
        if isinstance(error, app_commands.MissingPermissions):
            embed = discord.Embed(
                title="\u274C Permission refusee",
                description="Vous n'avez pas les permissions necessaires pour utiliser cette commande.",
                color=discord.Color.red()
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)

    @ban_player.error
    @unban_player.error
    async def ban_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Gere les erreurs de permissions pour les commandes de ban."""
        if isinstance(error, app_commands.MissingPermissions):
            embed = discord.Embed(
                title="\u274C Permission refusee",
                description="Vous devez avoir la permission de bannir des membres pour utiliser cette commande.",
                color=discord.Color.red()
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Charge le cog."""
    await bot.add_cog(PlayersCog(bot))
