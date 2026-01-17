"""
Cog de gestion du serveur Minecraft.
Commandes pour gérer l'état du serveur, les backups et les logs.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Literal
from datetime import datetime, timedelta
from enum import Enum
import asyncio


class Permission(Enum):
    """Niveaux de permission pour les commandes."""
    PLAYER = 0
    MODERATOR = 1
    ADMIN = 2


class ServerState(Enum):
    """États possibles du serveur."""
    ONLINE = "online"
    OFFLINE = "offline"
    STARTING = "starting"
    STOPPING = "stopping"
    RESTARTING = "restarting"


# Couleurs pour les embeds selon l'état
STATE_COLORS = {
    ServerState.ONLINE: discord.Color.green(),
    ServerState.OFFLINE: discord.Color.red(),
    ServerState.STARTING: discord.Color.yellow(),
    ServerState.STOPPING: discord.Color.orange(),
    ServerState.RESTARTING: discord.Color.blue(),
}

STATE_EMOJIS = {
    ServerState.ONLINE: ":green_circle:",
    ServerState.OFFLINE: ":red_circle:",
    ServerState.STARTING: ":yellow_circle:",
    ServerState.STOPPING: ":orange_circle:",
    ServerState.RESTARTING: ":blue_circle:",
}


class ConfirmationView(discord.ui.View):
    """View avec boutons de confirmation pour les actions sensibles."""

    def __init__(self, author: discord.User, action: str, timeout: float = 30.0):
        super().__init__(timeout=timeout)
        self.author = author
        self.action = action
        self.value: Optional[bool] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Vérifie que seul l'auteur peut interagir."""
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "Vous ne pouvez pas interagir avec cette confirmation.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Confirmer", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bouton de confirmation."""
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bouton d'annulation."""
        self.value = False
        self.stop()
        await interaction.response.defer()


class BackupPaginationView(discord.ui.View):
    """View pour la pagination des backups."""

    def __init__(self, backups: list, author: discord.User, per_page: int = 10):
        super().__init__(timeout=60.0)
        self.backups = backups
        self.author = author
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = max(1, (len(backups) + per_page - 1) // per_page)
        self.update_buttons()

    def update_buttons(self):
        """Met à jour l'état des boutons."""
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1

    def get_embed(self) -> discord.Embed:
        """Génère l'embed pour la page actuelle."""
        embed = discord.Embed(
            title=":file_folder: Liste des Backups",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        if not self.backups:
            embed.description = "Aucun backup disponible."
            return embed

        start = self.current_page * self.per_page
        end = start + self.per_page
        page_backups = self.backups[start:end]

        description_lines = []
        for backup in page_backups:
            name = backup.get("name", "Unknown")
            date = backup.get("created_at", "N/A")
            size = backup.get("size", "N/A")
            description_lines.append(f"**{name}** - {date} ({size})")

        embed.description = "\n".join(description_lines)
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages}")

        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Vérifie que seul l'auteur peut interagir."""
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "Vous ne pouvez pas interagir avec cette pagination.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Précédent", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bouton page précédente."""
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Suivant", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bouton page suivante."""
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


class ServerCog(commands.Cog):
    """Cog pour la gestion du serveur Minecraft."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.server_state = ServerState.OFFLINE
        self.start_time: Optional[datetime] = None

    # ==================== Helpers ====================

    async def check_permission(
        self,
        interaction: discord.Interaction,
        required: Permission
    ) -> bool:
        """
        Vérifie les permissions de l'utilisateur.
        Retourne True si l'utilisateur a la permission requise.
        """
        member = interaction.user

        if not isinstance(member, discord.Member):
            return False

        # Admin: a la permission administrateur
        if member.guild_permissions.administrator:
            return True

        # Vérification par rôles
        role_names = [role.name.lower() for role in member.roles]

        if required == Permission.ADMIN:
            return "admin" in role_names or "administrateur" in role_names

        if required == Permission.MODERATOR:
            return any(r in role_names for r in ["admin", "administrateur", "moderator", "modérateur", "mod"])

        # PLAYER - tout le monde
        return True

    async def log_action(
        self,
        action: str,
        user: discord.User,
        details: Optional[str] = None,
        success: bool = True
    ):
        """
        Enregistre une action dans la base de données.
        À implémenter avec votre système de DB.
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "user_id": user.id,
            "user_name": str(user),
            "details": details,
            "success": success
        }

        # TODO: Implémenter la connexion à votre DB
        # await self.bot.db.logs.insert_one(log_entry)

        print(f"[LOG] {log_entry}")

    def get_uptime(self) -> str:
        """Calcule et formate l'uptime du serveur."""
        if not self.start_time or self.server_state != ServerState.ONLINE:
            return "N/A"

        delta = datetime.utcnow() - self.start_time
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days}j")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")

        return " ".join(parts)

    async def get_server_info(self) -> dict:
        """
        Récupère les informations du serveur.
        À implémenter avec votre système de monitoring.
        """
        # TODO: Implémenter la récupération réelle des données
        # Exemple avec RCON ou API du serveur

        return {
            "state": self.server_state,
            "players_online": 5,
            "players_max": 20,
            "players_list": ["Player1", "Player2", "Player3", "Player4", "Player5"],
            "tps": 19.8,
            "ram_used": 4096,  # MB
            "ram_max": 8192,  # MB
            "version": "1.20.4",
            "motd": "Serveur Minecraft"
        }

    async def execute_server_command(self, command: str) -> bool:
        """
        Exécute une commande sur le serveur.
        À implémenter avec RCON ou votre système.
        """
        # TODO: Implémenter l'exécution réelle des commandes
        # Exemple: await self.rcon.execute(command)

        await asyncio.sleep(1)  # Simulation
        return True

    async def get_server_logs(self, lines: int = 20) -> list[str]:
        """
        Récupère les dernières lignes de logs.
        À implémenter avec votre système de logs.
        """
        # TODO: Implémenter la lecture réelle des logs
        # Exemple: lecture du fichier latest.log

        return [
            "[12:00:00] [Server thread/INFO]: Server started",
            "[12:01:00] [Server thread/INFO]: Player1 joined the game",
            "[12:02:00] [Server thread/INFO]: Player2 joined the game",
        ]

    async def create_backup(self, name: str) -> dict:
        """
        Crée un backup du serveur.
        À implémenter avec votre système de backup.
        """
        # TODO: Implémenter la création réelle de backup

        return {
            "name": name,
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "size": "1.5 GB",
            "success": True
        }

    async def get_backups(self) -> list[dict]:
        """
        Récupère la liste des backups.
        À implémenter avec votre système de backup.
        """
        # TODO: Implémenter la récupération réelle des backups

        return [
            {"name": "backup_2024_01_15_auto", "created_at": "2024-01-15 00:00:00", "size": "1.5 GB"},
            {"name": "backup_2024_01_14_auto", "created_at": "2024-01-14 00:00:00", "size": "1.4 GB"},
            {"name": "backup_manual_test", "created_at": "2024-01-13 15:30:00", "size": "1.4 GB"},
        ]

    async def restore_backup(self, name: str) -> bool:
        """
        Restaure un backup.
        À implémenter avec votre système de backup.
        """
        # TODO: Implémenter la restauration réelle

        await asyncio.sleep(2)  # Simulation
        return True

    # ==================== Groupe de commandes /server ====================

    server_group = app_commands.Group(name="server", description="Commandes de gestion du serveur Minecraft")

    @server_group.command(name="status", description="Affiche l'état actuel du serveur")
    async def server_status(self, interaction: discord.Interaction):
        """Affiche un embed avec l'état du serveur."""
        await interaction.response.defer()

        info = await self.get_server_info()
        state = info["state"]

        embed = discord.Embed(
            title=f"{STATE_EMOJIS[state]} Statut du Serveur",
            color=STATE_COLORS[state],
            timestamp=datetime.utcnow()
        )

        # État général
        state_text = {
            ServerState.ONLINE: "En ligne",
            ServerState.OFFLINE: "Hors ligne",
            ServerState.STARTING: "Démarrage en cours...",
            ServerState.STOPPING: "Arrêt en cours...",
            ServerState.RESTARTING: "Redémarrage en cours...",
        }
        embed.add_field(name="État", value=state_text[state], inline=True)
        embed.add_field(name="Version", value=info["version"], inline=True)
        embed.add_field(name="Uptime", value=self.get_uptime(), inline=True)

        if state == ServerState.ONLINE:
            # Joueurs
            players_str = f"{info['players_online']}/{info['players_max']}"
            embed.add_field(name=":busts_in_silhouette: Joueurs", value=players_str, inline=True)

            # TPS
            tps = info["tps"]
            tps_color = ":green_circle:" if tps >= 18 else ":yellow_circle:" if tps >= 15 else ":red_circle:"
            embed.add_field(name=f"{tps_color} TPS", value=f"{tps:.1f}/20", inline=True)

            # RAM
            ram_used = info["ram_used"]
            ram_max = info["ram_max"]
            ram_percent = (ram_used / ram_max) * 100
            ram_color = ":green_circle:" if ram_percent < 70 else ":yellow_circle:" if ram_percent < 90 else ":red_circle:"
            embed.add_field(
                name=f"{ram_color} RAM",
                value=f"{ram_used}MB / {ram_max}MB ({ram_percent:.1f}%)",
                inline=True
            )

            # Liste des joueurs
            if info["players_list"]:
                players_list = ", ".join(info["players_list"][:10])
                if len(info["players_list"]) > 10:
                    players_list += f" (+{len(info['players_list']) - 10} autres)"
                embed.add_field(name="Joueurs connectés", value=players_list, inline=False)

        embed.set_footer(text=f"Demandé par {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)

    @server_group.command(name="start", description="Démarre le serveur Minecraft")
    async def server_start(self, interaction: discord.Interaction):
        """Démarre le serveur (Admin uniquement)."""
        if not await self.check_permission(interaction, Permission.ADMIN):
            await interaction.response.send_message(
                ":x: Vous n'avez pas la permission d'exécuter cette commande.",
                ephemeral=True
            )
            return

        if self.server_state == ServerState.ONLINE:
            await interaction.response.send_message(
                ":warning: Le serveur est déjà en ligne.",
                ephemeral=True
            )
            return

        if self.server_state in [ServerState.STARTING, ServerState.STOPPING, ServerState.RESTARTING]:
            await interaction.response.send_message(
                f":warning: Une opération est déjà en cours ({self.server_state.value}).",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        self.server_state = ServerState.STARTING

        embed = discord.Embed(
            title=":yellow_circle: Démarrage du serveur",
            description="Le serveur est en cours de démarrage...",
            color=STATE_COLORS[ServerState.STARTING],
            timestamp=datetime.utcnow()
        )
        message = await interaction.followup.send(embed=embed)

        # TODO: Implémenter le démarrage réel du serveur
        success = await self.execute_server_command("start")

        if success:
            self.server_state = ServerState.ONLINE
            self.start_time = datetime.utcnow()

            embed = discord.Embed(
                title=":green_circle: Serveur démarré",
                description="Le serveur Minecraft est maintenant en ligne !",
                color=STATE_COLORS[ServerState.ONLINE],
                timestamp=datetime.utcnow()
            )
            await self.log_action("server_start", interaction.user, success=True)
        else:
            self.server_state = ServerState.OFFLINE

            embed = discord.Embed(
                title=":x: Échec du démarrage",
                description="Le serveur n'a pas pu démarrer. Consultez les logs pour plus d'informations.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await self.log_action("server_start", interaction.user, details="Échec", success=False)

        await message.edit(embed=embed)

    @server_group.command(name="stop", description="Arrête le serveur Minecraft")
    @app_commands.describe(force="Forcer l'arrêt immédiat sans sauvegarde")
    async def server_stop(
        self,
        interaction: discord.Interaction,
        force: Optional[bool] = False
    ):
        """Arrête le serveur avec confirmation (Admin uniquement)."""
        if not await self.check_permission(interaction, Permission.ADMIN):
            await interaction.response.send_message(
                ":x: Vous n'avez pas la permission d'exécuter cette commande.",
                ephemeral=True
            )
            return

        if self.server_state == ServerState.OFFLINE:
            await interaction.response.send_message(
                ":warning: Le serveur est déjà hors ligne.",
                ephemeral=True
            )
            return

        if self.server_state in [ServerState.STARTING, ServerState.STOPPING, ServerState.RESTARTING]:
            await interaction.response.send_message(
                f":warning: Une opération est déjà en cours ({self.server_state.value}).",
                ephemeral=True
            )
            return

        # Demande de confirmation
        info = await self.get_server_info()
        players_online = info["players_online"]

        confirm_embed = discord.Embed(
            title=":warning: Confirmation d'arrêt",
            description=f"Êtes-vous sûr de vouloir arrêter le serveur ?\n\n"
                       f"**Joueurs connectés:** {players_online}\n"
                       f"**Mode:** {'Force' if force else 'Normal'}",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        view = ConfirmationView(interaction.user, "stop")
        await interaction.response.send_message(embed=confirm_embed, view=view)

        await view.wait()

        if view.value is None:
            timeout_embed = discord.Embed(
                title=":clock1: Temps écoulé",
                description="La confirmation a expiré.",
                color=discord.Color.grey()
            )
            await interaction.edit_original_response(embed=timeout_embed, view=None)
            return

        if not view.value:
            cancel_embed = discord.Embed(
                title=":x: Annulé",
                description="L'arrêt du serveur a été annulé.",
                color=discord.Color.grey()
            )
            await interaction.edit_original_response(embed=cancel_embed, view=None)
            return

        # Procéder à l'arrêt
        self.server_state = ServerState.STOPPING

        stopping_embed = discord.Embed(
            title=":orange_circle: Arrêt en cours",
            description="Le serveur est en cours d'arrêt...",
            color=STATE_COLORS[ServerState.STOPPING],
            timestamp=datetime.utcnow()
        )
        await interaction.edit_original_response(embed=stopping_embed, view=None)

        # TODO: Implémenter l'arrêt réel du serveur
        if force:
            success = await self.execute_server_command("stop force")
        else:
            success = await self.execute_server_command("stop")

        if success:
            self.server_state = ServerState.OFFLINE
            self.start_time = None

            embed = discord.Embed(
                title=":red_circle: Serveur arrêté",
                description="Le serveur Minecraft est maintenant hors ligne.",
                color=STATE_COLORS[ServerState.OFFLINE],
                timestamp=datetime.utcnow()
            )
            await self.log_action(
                "server_stop",
                interaction.user,
                details=f"Force: {force}",
                success=True
            )
        else:
            self.server_state = ServerState.ONLINE

            embed = discord.Embed(
                title=":x: Échec de l'arrêt",
                description="Le serveur n'a pas pu être arrêté. Consultez les logs.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await self.log_action("server_stop", interaction.user, details="Échec", success=False)

        await interaction.edit_original_response(embed=embed)

    @server_group.command(name="restart", description="Redémarre le serveur Minecraft")
    async def server_restart(self, interaction: discord.Interaction):
        """Redémarre le serveur (Admin uniquement)."""
        if not await self.check_permission(interaction, Permission.ADMIN):
            await interaction.response.send_message(
                ":x: Vous n'avez pas la permission d'exécuter cette commande.",
                ephemeral=True
            )
            return

        if self.server_state == ServerState.OFFLINE:
            await interaction.response.send_message(
                ":warning: Le serveur est hors ligne. Utilisez `/server start` pour le démarrer.",
                ephemeral=True
            )
            return

        if self.server_state in [ServerState.STARTING, ServerState.STOPPING, ServerState.RESTARTING]:
            await interaction.response.send_message(
                f":warning: Une opération est déjà en cours ({self.server_state.value}).",
                ephemeral=True
            )
            return

        # Demande de confirmation
        info = await self.get_server_info()
        players_online = info["players_online"]

        confirm_embed = discord.Embed(
            title=":warning: Confirmation de redémarrage",
            description=f"Êtes-vous sûr de vouloir redémarrer le serveur ?\n\n"
                       f"**Joueurs connectés:** {players_online}",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        view = ConfirmationView(interaction.user, "restart")
        await interaction.response.send_message(embed=confirm_embed, view=view)

        await view.wait()

        if view.value is None:
            timeout_embed = discord.Embed(
                title=":clock1: Temps écoulé",
                description="La confirmation a expiré.",
                color=discord.Color.grey()
            )
            await interaction.edit_original_response(embed=timeout_embed, view=None)
            return

        if not view.value:
            cancel_embed = discord.Embed(
                title=":x: Annulé",
                description="Le redémarrage du serveur a été annulé.",
                color=discord.Color.grey()
            )
            await interaction.edit_original_response(embed=cancel_embed, view=None)
            return

        # Procéder au redémarrage
        self.server_state = ServerState.RESTARTING

        restarting_embed = discord.Embed(
            title=":blue_circle: Redémarrage en cours",
            description="Le serveur est en cours de redémarrage...",
            color=STATE_COLORS[ServerState.RESTARTING],
            timestamp=datetime.utcnow()
        )
        await interaction.edit_original_response(embed=restarting_embed, view=None)

        # TODO: Implémenter le redémarrage réel du serveur
        success = await self.execute_server_command("restart")

        if success:
            self.server_state = ServerState.ONLINE
            self.start_time = datetime.utcnow()

            embed = discord.Embed(
                title=":green_circle: Serveur redémarré",
                description="Le serveur Minecraft a été redémarré avec succès !",
                color=STATE_COLORS[ServerState.ONLINE],
                timestamp=datetime.utcnow()
            )
            await self.log_action("server_restart", interaction.user, success=True)
        else:
            self.server_state = ServerState.OFFLINE

            embed = discord.Embed(
                title=":x: Échec du redémarrage",
                description="Le serveur n'a pas pu redémarrer. Consultez les logs.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await self.log_action("server_restart", interaction.user, details="Échec", success=False)

        await interaction.edit_original_response(embed=embed)

    @server_group.command(name="logs", description="Affiche les derniers logs du serveur")
    @app_commands.describe(lines="Nombre de lignes à afficher (défaut: 20, max: 50)")
    async def server_logs(
        self,
        interaction: discord.Interaction,
        lines: Optional[app_commands.Range[int, 1, 50]] = 20
    ):
        """Affiche les derniers logs du serveur."""
        await interaction.response.defer(ephemeral=True)

        logs = await self.get_server_logs(lines)

        if not logs:
            await interaction.followup.send(
                ":warning: Aucun log disponible.",
                ephemeral=True
            )
            return

        # Formater les logs
        log_text = "\n".join(logs[-lines:])

        # Limiter la taille pour Discord (max 4096 pour embed description)
        if len(log_text) > 4000:
            log_text = log_text[-4000:]
            log_text = "...\n" + log_text

        embed = discord.Embed(
            title=":scroll: Logs du serveur",
            description=f"```\n{log_text}\n```",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Dernières {lines} lignes")

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ==================== Sous-groupe /server backup ====================

    backup_group = app_commands.Group(
        name="backup",
        description="Commandes de gestion des backups",
        parent=server_group
    )

    @backup_group.command(name="create", description="Crée un nouveau backup du serveur")
    @app_commands.describe(name="Nom du backup (optionnel)")
    async def backup_create(
        self,
        interaction: discord.Interaction,
        name: Optional[str] = None
    ):
        """Crée un backup du serveur (Moderator+)."""
        if not await self.check_permission(interaction, Permission.MODERATOR):
            await interaction.response.send_message(
                ":x: Vous n'avez pas la permission d'exécuter cette commande.",
                ephemeral=True
            )
            return

        # Générer un nom par défaut si non fourni
        if not name:
            name = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        await interaction.response.defer()

        progress_embed = discord.Embed(
            title=":hourglass: Création du backup",
            description=f"Création du backup **{name}** en cours...",
            color=discord.Color.yellow(),
            timestamp=datetime.utcnow()
        )
        message = await interaction.followup.send(embed=progress_embed)

        result = await self.create_backup(name)

        if result["success"]:
            embed = discord.Embed(
                title=":white_check_mark: Backup créé",
                description=f"Le backup **{name}** a été créé avec succès !",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Nom", value=result["name"], inline=True)
            embed.add_field(name="Taille", value=result["size"], inline=True)
            embed.add_field(name="Date", value=result["created_at"], inline=True)

            await self.log_action(
                "backup_create",
                interaction.user,
                details=f"Nom: {name}",
                success=True
            )
        else:
            embed = discord.Embed(
                title=":x: Échec du backup",
                description="Le backup n'a pas pu être créé. Consultez les logs.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await self.log_action(
                "backup_create",
                interaction.user,
                details=f"Nom: {name}, Échec",
                success=False
            )

        await message.edit(embed=embed)

    @backup_group.command(name="list", description="Liste tous les backups disponibles")
    async def backup_list(self, interaction: discord.Interaction):
        """Liste les backups disponibles."""
        await interaction.response.defer()

        backups = await self.get_backups()

        view = BackupPaginationView(backups, interaction.user)
        embed = view.get_embed()

        await interaction.followup.send(embed=embed, view=view)

    @backup_group.command(name="restore", description="Restaure un backup")
    @app_commands.describe(name="Nom du backup à restaurer")
    async def backup_restore(
        self,
        interaction: discord.Interaction,
        name: str
    ):
        """Restaure un backup (Admin uniquement)."""
        if not await self.check_permission(interaction, Permission.ADMIN):
            await interaction.response.send_message(
                ":x: Vous n'avez pas la permission d'exécuter cette commande.",
                ephemeral=True
            )
            return

        # Vérifier que le backup existe
        backups = await self.get_backups()
        backup_names = [b["name"] for b in backups]

        if name not in backup_names:
            await interaction.response.send_message(
                f":x: Le backup **{name}** n'existe pas.\n"
                f"Utilisez `/server backup list` pour voir les backups disponibles.",
                ephemeral=True
            )
            return

        # Demande de confirmation
        confirm_embed = discord.Embed(
            title=":warning: Confirmation de restauration",
            description=f"Êtes-vous sûr de vouloir restaurer le backup **{name}** ?\n\n"
                       f":warning: **Attention:** Cette action est irréversible et écrasera "
                       f"les données actuelles du serveur !",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        view = ConfirmationView(interaction.user, "restore")
        await interaction.response.send_message(embed=confirm_embed, view=view)

        await view.wait()

        if view.value is None:
            timeout_embed = discord.Embed(
                title=":clock1: Temps écoulé",
                description="La confirmation a expiré.",
                color=discord.Color.grey()
            )
            await interaction.edit_original_response(embed=timeout_embed, view=None)
            return

        if not view.value:
            cancel_embed = discord.Embed(
                title=":x: Annulé",
                description="La restauration a été annulée.",
                color=discord.Color.grey()
            )
            await interaction.edit_original_response(embed=cancel_embed, view=None)
            return

        # Procéder à la restauration
        restoring_embed = discord.Embed(
            title=":hourglass: Restauration en cours",
            description=f"Restauration du backup **{name}** en cours...\n"
                       f"Le serveur sera indisponible pendant cette opération.",
            color=discord.Color.yellow(),
            timestamp=datetime.utcnow()
        )
        await interaction.edit_original_response(embed=restoring_embed, view=None)

        # Arrêter le serveur si nécessaire
        previous_state = self.server_state
        if self.server_state == ServerState.ONLINE:
            self.server_state = ServerState.STOPPING
            await self.execute_server_command("stop")

        self.server_state = ServerState.OFFLINE

        # Restaurer le backup
        success = await self.restore_backup(name)

        if success:
            embed = discord.Embed(
                title=":white_check_mark: Backup restauré",
                description=f"Le backup **{name}** a été restauré avec succès !\n"
                           f"Utilisez `/server start` pour démarrer le serveur.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await self.log_action(
                "backup_restore",
                interaction.user,
                details=f"Backup: {name}",
                success=True
            )
        else:
            embed = discord.Embed(
                title=":x: Échec de la restauration",
                description="La restauration a échoué. Consultez les logs.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await self.log_action(
                "backup_restore",
                interaction.user,
                details=f"Backup: {name}, Échec",
                success=False
            )

        await interaction.edit_original_response(embed=embed)


async def setup(bot: commands.Bot):
    """Charge le cog."""
    await bot.add_cog(ServerCog(bot))
