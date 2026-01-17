"""
Cog de monitoring du serveur Minecraft.
Collecte et affiche les statistiques du serveur (TPS, RAM, CPU, joueurs, uptime).
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import re
import psutil
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

# Configuration du logger
logger = logging.getLogger(__name__)

# Cache pour le TPS
_tps_cache: Dict[str, Any] = {"value": None, "timestamp": 0.0}
TPS_CACHE_TTL = 5  # 5 secondes


class MonitoringCog(commands.Cog):
    """Cog pour le monitoring du serveur Minecraft."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.stats_history: deque[Dict[str, Any]] = deque(maxlen=1440)  # 12 heures de données (30s * 1440 = 12h)
        self.status_message_id: Optional[int] = None
        self.status_channel_id: Optional[int] = None
        self.server_start_time: Optional[datetime] = None
        self.last_stats: Dict[str, Any] = {}

        # Seuils d'alerte
        self.thresholds = {
            'tps': {'warning': 15, 'critical': 10},
            'ram': {'warning': 80, 'critical': 90},
            'cpu': {'warning': 80, 'critical': 95}
        }

        # Démarrer la task loop
        self.collect_stats_loop.start()

    def cog_unload(self):
        """Arrêter la task loop lors du déchargement du cog."""
        self.collect_stats_loop.cancel()

    # ============================================================
    # UTILITAIRES
    # ============================================================

    def get_status_emoji(self, value: float, metric: str) -> str:
        """Retourne l'emoji approprié selon la valeur et le type de métrique."""
        thresholds = self.thresholds.get(metric, {})
        warning = thresholds.get('warning', 0)
        critical = thresholds.get('critical', 0)

        if metric == 'tps':
            # Pour TPS, plus c'est haut, mieux c'est
            if value >= warning:
                return '🟢'
            elif value >= critical:
                return '🟡'
            else:
                return '🔴'
        else:
            # Pour RAM/CPU, plus c'est bas, mieux c'est
            if value < warning:
                return '🟢'
            elif value < critical:
                return '🟡'
            else:
                return '🔴'

    def create_progress_bar(self, value: float, max_value: float = 100, length: int = 10) -> str:
        """Crée une barre de progression visuelle."""
        percentage = min(value / max_value, 1.0)
        filled = int(percentage * length)
        empty = length - filled

        if percentage < 0.6:
            fill_char = '🟩'
        elif percentage < 0.8:
            fill_char = '🟨'
        else:
            fill_char = '🟥'

        return fill_char * filled + '⬜' * empty

    def create_tps_bar(self, tps: float) -> str:
        """Crée une barre visuelle pour le TPS (max 20)."""
        percentage = min(tps / 20.0, 1.0)
        filled = int(percentage * 10)
        empty = 10 - filled

        if tps >= 18:
            fill_char = '🟩'
        elif tps >= 15:
            fill_char = '🟨'
        else:
            fill_char = '🟥'

        return fill_char * filled + '⬜' * empty

    def create_ascii_graph(self, data: List[float], height: int = 5, width: int = 20) -> str:
        """Crée un graphique ASCII simple."""
        if not data:
            return "Pas de données disponibles"

        # Prendre les dernières 'width' valeurs
        data = data[-width:]

        if len(data) < 2:
            return "Pas assez de données"

        min_val = min(data)
        max_val = max(data)
        range_val = max_val - min_val if max_val != min_val else 1

        graph_chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']

        graph = ""
        for val in data:
            normalized = (val - min_val) / range_val
            char_index = min(int(normalized * (len(graph_chars) - 1)), len(graph_chars) - 1)
            graph += graph_chars[char_index]

        return f"```\n{graph}\nMin: {min_val:.1f} | Max: {max_val:.1f}\n```"

    def format_uptime(self, start_time: Optional[datetime]) -> str:
        """Formate l'uptime du serveur."""
        if not start_time:
            return "Inconnu"

        delta = datetime.now() - start_time
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
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")

        return " ".join(parts)

    def format_bytes(self, bytes_value: int) -> str:
        """Formate les bytes en format lisible."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"

    # ============================================================
    # COLLECTE DE DONNÉES
    # ============================================================

    async def get_tps_from_rcon(self) -> Optional[float]:
        """Récupère le TPS via RCON avec la commande 'forge tps' et cache de 5 secondes."""
        global _tps_cache

        try:
            # Vérifier le cache
            now = asyncio.get_running_loop().time()
            if _tps_cache["value"] is not None and (now - _tps_cache["timestamp"]) < TPS_CACHE_TTL:
                return _tps_cache["value"]

            rcon_cog = self.bot.get_cog('RCONCog')
            if not rcon_cog:
                return None

            response = await rcon_cog.execute_command("forge tps")
            if not response:
                return None

            # Parser la réponse de forge tps
            # Format typique: "Dim 0 (overworld): Mean tick time: 12.34 ms. Mean TPS: 20.00"
            tps_match = re.search(r'Mean TPS:\s*([\d.]+)', response)
            if tps_match:
                tps = float(tps_match.group(1))
                _tps_cache["value"] = tps
                _tps_cache["timestamp"] = now
                return tps

            # Format alternatif
            tps_match = re.search(r'TPS:\s*([\d.]+)', response, re.IGNORECASE)
            if tps_match:
                tps = float(tps_match.group(1))
                _tps_cache["value"] = tps
                _tps_cache["timestamp"] = now
                return tps

            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du TPS: {e}")
            return None

    async def get_player_count(self) -> Tuple[int, int, List[str]]:
        """Récupère le nombre de joueurs via RCON."""
        try:
            rcon_cog = self.bot.get_cog('RCONCog')
            if not rcon_cog:
                return 0, 20, []

            response = await rcon_cog.execute_command("list")
            if not response:
                return 0, 20, []

            # Parser la réponse
            # Format: "There are X of a max of Y players online: player1, player2"
            match = re.search(r'(\d+)\s+(?:of a max of|/)\s*(\d+)', response)
            if match:
                online = int(match.group(1))
                max_players = int(match.group(2))

                # Extraire les noms des joueurs
                players = []
                if ':' in response:
                    player_list = response.split(':')[-1].strip()
                    if player_list:
                        players = [p.strip() for p in player_list.split(',') if p.strip()]

                return online, max_players, players

            return 0, 20, []
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des joueurs: {e}")
            return 0, 20, []

    def get_system_stats(self) -> Dict[str, float]:
        """Récupère les statistiques système (RAM, CPU)."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()

            return {
                'cpu_percent': cpu_percent,
                'ram_percent': memory.percent,
                'ram_used': memory.used,
                'ram_total': memory.total,
                'ram_available': memory.available
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stats système: {e}")
            return {
                'cpu_percent': 0,
                'ram_percent': 0,
                'ram_used': 0,
                'ram_total': 0,
                'ram_available': 0
            }

    async def collect_all_stats(self) -> Dict[str, Any]:
        """Collecte toutes les statistiques en parallèle."""
        # Exécuter les appels async en parallèle avec asyncio.gather
        tps_result, player_result = await asyncio.gather(
            self.get_tps_from_rcon(),
            self.get_player_count(),
            return_exceptions=True
        )

        # Gérer les exceptions potentielles
        tps = tps_result if not isinstance(tps_result, Exception) else None
        if isinstance(player_result, Exception):
            online, max_players, players = 0, 20, []
        else:
            online, max_players, players = player_result

        # get_system_stats est synchrone
        system_stats = self.get_system_stats()

        stats = {
            'timestamp': datetime.now(),
            'tps': tps,
            'players_online': online,
            'players_max': max_players,
            'player_names': players,
            **system_stats
        }

        return stats

    # ============================================================
    # STOCKAGE EN BASE DE DONNÉES
    # ============================================================

    async def save_stats_to_db(self, stats: Dict[str, Any]):
        """Sauvegarde les stats dans la base de données."""
        try:
            db_cog = self.bot.get_cog('DatabaseCog')
            if not db_cog:
                return

            await db_cog.execute("""
                INSERT INTO server_stats (timestamp, tps, cpu_percent, ram_percent,
                                          ram_used, players_online)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                stats['timestamp'].isoformat(),
                stats.get('tps'),
                stats.get('cpu_percent'),
                stats.get('ram_percent'),
                stats.get('ram_used'),
                stats.get('players_online')
            ))
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des stats: {e}")

    async def get_stats_history_from_db(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Récupère l'historique des stats depuis la base de données."""
        try:
            db_cog = self.bot.get_cog('DatabaseCog')
            if not db_cog:
                return self.stats_history

            since = datetime.now() - timedelta(hours=hours)
            rows = await db_cog.fetchall("""
                SELECT timestamp, tps, cpu_percent, ram_percent, ram_used, players_online
                FROM server_stats
                WHERE timestamp > ?
                ORDER BY timestamp ASC
            """, (since.isoformat(),))

            return [
                {
                    'timestamp': row[0],
                    'tps': row[1],
                    'cpu_percent': row[2],
                    'ram_percent': row[3],
                    'ram_used': row[4],
                    'players_online': row[5]
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique: {e}")
            return list(self.stats_history)

    # ============================================================
    # ALERTES
    # ============================================================

    async def check_and_send_alerts(self, stats: Dict[str, Any]):
        """Vérifie les seuils et envoie des alertes si nécessaire."""
        alerts = []

        # Vérifier TPS
        tps = stats.get('tps')
        if tps is not None:
            if tps < self.thresholds['tps']['critical']:
                alerts.append({
                    'level': 'critical',
                    'message': f"🔴 **ALERTE CRITIQUE** - TPS très bas: {tps:.1f}",
                    'metric': 'tps',
                    'value': tps
                })
            elif tps < self.thresholds['tps']['warning']:
                alerts.append({
                    'level': 'warning',
                    'message': f"🟡 **Attention** - TPS bas: {tps:.1f}",
                    'metric': 'tps',
                    'value': tps
                })

        # Vérifier RAM
        ram = stats.get('ram_percent', 0)
        if ram >= self.thresholds['ram']['critical']:
            alerts.append({
                'level': 'critical',
                'message': f"🔴 **ALERTE CRITIQUE** - RAM critique: {ram:.1f}%",
                'metric': 'ram',
                'value': ram
            })
        elif ram >= self.thresholds['ram']['warning']:
            alerts.append({
                'level': 'warning',
                'message': f"🟡 **Attention** - RAM élevée: {ram:.1f}%",
                'metric': 'ram',
                'value': ram
            })

        # Vérifier CPU
        cpu = stats.get('cpu_percent', 0)
        if cpu >= self.thresholds['cpu']['critical']:
            alerts.append({
                'level': 'critical',
                'message': f"🔴 **ALERTE CRITIQUE** - CPU critique: {cpu:.1f}%",
                'metric': 'cpu',
                'value': cpu
            })
        elif cpu >= self.thresholds['cpu']['warning']:
            alerts.append({
                'level': 'warning',
                'message': f"🟡 **Attention** - CPU élevé: {cpu:.1f}%",
                'metric': 'cpu',
                'value': cpu
            })

        # Envoyer les alertes
        for alert in alerts:
            await self.send_alert(alert)

    async def send_alert(self, alert: Dict[str, Any]):
        """Envoie une alerte dans le channel configuré."""
        try:
            config_cog = self.bot.get_cog('ConfigCog')
            if not config_cog:
                return

            alert_channel_id = await config_cog.get_config('alert_channel_id')
            if not alert_channel_id:
                return

            channel = self.bot.get_channel(int(alert_channel_id))
            if not channel:
                return

            color = discord.Color.red() if alert['level'] == 'critical' else discord.Color.yellow()

            embed = discord.Embed(
                title="Alerte Serveur",
                description=alert['message'],
                color=color,
                timestamp=datetime.now()
            )

            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'alerte: {e}")

    # ============================================================
    # STATUS AUTO-UPDATE
    # ============================================================

    async def update_status_message(self, stats: Dict[str, Any]):
        """Met à jour le message de status dans le channel dédié."""
        try:
            config_cog = self.bot.get_cog('ConfigCog')
            if not config_cog:
                return

            status_channel_id = await config_cog.get_config('status_channel_id')
            status_message_id = await config_cog.get_config('status_message_id')

            if not status_channel_id:
                return

            channel = self.bot.get_channel(int(status_channel_id))
            if not channel:
                return

            embed = await self.create_stats_embed(stats)

            if status_message_id:
                try:
                    message = await channel.fetch_message(int(status_message_id))
                    await message.edit(embed=embed)
                    return
                except discord.NotFound:
                    pass

            # Créer un nouveau message si nécessaire
            message = await channel.send(embed=embed)
            await config_cog.set_config('status_message_id', str(message.id))
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du status: {e}")

    async def create_stats_embed(self, stats: Dict[str, Any]) -> discord.Embed:
        """Crée l'embed des statistiques."""
        tps = stats.get('tps')
        cpu = stats.get('cpu_percent', 0)
        ram = stats.get('ram_percent', 0)
        ram_used = stats.get('ram_used', 0)
        ram_total = stats.get('ram_total', 0)
        players_online = stats.get('players_online', 0)
        players_max = stats.get('players_max', 20)
        player_names = stats.get('player_names', [])

        # Déterminer la couleur de l'embed
        if tps is not None and tps < self.thresholds['tps']['critical']:
            color = discord.Color.red()
        elif tps is not None and tps < self.thresholds['tps']['warning']:
            color = discord.Color.yellow()
        elif ram >= self.thresholds['ram']['critical'] or cpu >= self.thresholds['cpu']['critical']:
            color = discord.Color.red()
        elif ram >= self.thresholds['ram']['warning'] or cpu >= self.thresholds['cpu']['warning']:
            color = discord.Color.yellow()
        else:
            color = discord.Color.green()

        embed = discord.Embed(
            title="📊 Status du Serveur Minecraft",
            color=color,
            timestamp=datetime.now()
        )

        # TPS
        if tps is not None:
            tps_emoji = self.get_status_emoji(tps, 'tps')
            tps_bar = self.create_tps_bar(tps)
            embed.add_field(
                name=f"{tps_emoji} TPS",
                value=f"**{tps:.1f}**/20\n{tps_bar}",
                inline=True
            )
        else:
            embed.add_field(
                name="⚪ TPS",
                value="Non disponible",
                inline=True
            )

        # CPU
        cpu_emoji = self.get_status_emoji(cpu, 'cpu')
        cpu_bar = self.create_progress_bar(cpu)
        embed.add_field(
            name=f"{cpu_emoji} CPU",
            value=f"**{cpu:.1f}%**\n{cpu_bar}",
            inline=True
        )

        # RAM
        ram_emoji = self.get_status_emoji(ram, 'ram')
        ram_bar = self.create_progress_bar(ram)
        embed.add_field(
            name=f"{ram_emoji} RAM",
            value=f"**{ram:.1f}%** ({self.format_bytes(ram_used)}/{self.format_bytes(ram_total)})\n{ram_bar}",
            inline=True
        )

        # Joueurs
        player_text = f"**{players_online}**/{players_max}"
        if player_names:
            player_text += f"\n`{', '.join(player_names[:10])}`"
            if len(player_names) > 10:
                player_text += f"\n... et {len(player_names) - 10} autres"
        embed.add_field(
            name="👥 Joueurs",
            value=player_text,
            inline=True
        )

        # Uptime
        embed.add_field(
            name="⏱️ Uptime",
            value=self.format_uptime(self.server_start_time),
            inline=True
        )

        embed.set_footer(text="Mise à jour toutes les 30 secondes")

        return embed

    # ============================================================
    # TASK LOOP
    # ============================================================

    @tasks.loop(seconds=30)
    async def collect_stats_loop(self) -> None:
        """Task loop pour collecter les stats toutes les 30 secondes."""
        try:
            stats = await self.collect_all_stats()
            self.last_stats = stats

            # Ajouter à l'historique en mémoire (deque gère automatiquement la taille max)
            self.stats_history.append(stats)

            # Sauvegarder en DB
            await self.save_stats_to_db(stats)

            # Vérifier les alertes
            await self.check_and_send_alerts(stats)

            # Mettre à jour le message de status
            await self.update_status_message(stats)
        except Exception as e:
            logger.error(f"Erreur dans la collecte de stats: {e}")

    @collect_stats_loop.before_loop
    async def before_collect_stats(self):
        """Attendre que le bot soit prêt avant de démarrer la loop."""
        await self.bot.wait_until_ready()
        self.server_start_time = datetime.now()

    # ============================================================
    # COMMANDES SLASH
    # ============================================================

    @app_commands.command(name="stats", description="Affiche les statistiques complètes du serveur")
    async def stats_command(self, interaction: discord.Interaction):
        """Affiche les stats complètes du serveur."""
        await interaction.response.defer()

        stats = await self.collect_all_stats()
        embed = await self.create_stats_embed(stats)

        # Ajouter plus de détails pour la commande complète
        history = await self.get_stats_history_from_db(hours=1)
        if history:
            tps_values = [s.get('tps') for s in history if s.get('tps') is not None]
            cpu_values = [s.get('cpu_percent') for s in history if s.get('cpu_percent') is not None]
            ram_values = [s.get('ram_percent') for s in history if s.get('ram_percent') is not None]

            if tps_values:
                avg_tps = sum(tps_values) / len(tps_values)
                embed.add_field(
                    name="📈 Moyenne TPS (1h)",
                    value=f"{avg_tps:.1f}",
                    inline=True
                )

            if cpu_values:
                avg_cpu = sum(cpu_values) / len(cpu_values)
                embed.add_field(
                    name="📈 Moyenne CPU (1h)",
                    value=f"{avg_cpu:.1f}%",
                    inline=True
                )

            if ram_values:
                avg_ram = sum(ram_values) / len(ram_values)
                embed.add_field(
                    name="📈 Moyenne RAM (1h)",
                    value=f"{avg_ram:.1f}%",
                    inline=True
                )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="tps", description="Affiche le TPS actuel du serveur")
    async def tps_command(self, interaction: discord.Interaction):
        """Affiche le TPS actuel avec indicateur visuel."""
        await interaction.response.defer()

        tps = await self.get_tps_from_rcon()

        if tps is None:
            embed = discord.Embed(
                title="⚪ TPS",
                description="Impossible de récupérer le TPS du serveur.\nVérifiez que le serveur est en ligne et que RCON est configuré.",
                color=discord.Color.greyple()
            )
            await interaction.followup.send(embed=embed)
            return

        tps_emoji = self.get_status_emoji(tps, 'tps')
        tps_bar = self.create_tps_bar(tps)

        # Déterminer la couleur
        if tps >= 18:
            color = discord.Color.green()
            status = "Excellent"
        elif tps >= 15:
            color = discord.Color.yellow()
            status = "Correct"
        elif tps >= 10:
            color = discord.Color.orange()
            status = "Dégradé"
        else:
            color = discord.Color.red()
            status = "Critique"

        embed = discord.Embed(
            title=f"{tps_emoji} TPS du Serveur",
            color=color,
            timestamp=datetime.now()
        )

        embed.add_field(
            name="TPS Actuel",
            value=f"**{tps:.2f}** / 20",
            inline=True
        )

        embed.add_field(
            name="Status",
            value=status,
            inline=True
        )

        embed.add_field(
            name="Jauge",
            value=tps_bar,
            inline=False
        )

        # Historique TPS
        history = await self.get_stats_history_from_db(hours=1)
        tps_values = [s.get('tps') for s in history if s.get('tps') is not None]

        if tps_values:
            embed.add_field(
                name="📊 Historique (1h)",
                value=self.create_ascii_graph(tps_values),
                inline=False
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="performance", description="Affiche les détails de performance RAM/CPU")
    async def performance_command(self, interaction: discord.Interaction):
        """Affiche les détails RAM/CPU avec graphique ASCII."""
        await interaction.response.defer()

        stats = self.get_system_stats()

        cpu = stats['cpu_percent']
        ram = stats['ram_percent']
        ram_used = stats['ram_used']
        ram_total = stats['ram_total']
        ram_available = stats['ram_available']

        cpu_emoji = self.get_status_emoji(cpu, 'cpu')
        ram_emoji = self.get_status_emoji(ram, 'ram')

        # Déterminer la couleur globale
        if cpu >= self.thresholds['cpu']['critical'] or ram >= self.thresholds['ram']['critical']:
            color = discord.Color.red()
        elif cpu >= self.thresholds['cpu']['warning'] or ram >= self.thresholds['ram']['warning']:
            color = discord.Color.yellow()
        else:
            color = discord.Color.green()

        embed = discord.Embed(
            title="⚙️ Performance du Système",
            color=color,
            timestamp=datetime.now()
        )

        # CPU
        cpu_bar = self.create_progress_bar(cpu)
        embed.add_field(
            name=f"{cpu_emoji} CPU",
            value=f"**{cpu:.1f}%**\n{cpu_bar}",
            inline=True
        )

        # RAM détaillée
        ram_bar = self.create_progress_bar(ram)
        embed.add_field(
            name=f"{ram_emoji} RAM",
            value=f"**{ram:.1f}%**\n{ram_bar}",
            inline=True
        )

        embed.add_field(
            name="💾 Détails RAM",
            value=(
                f"**Utilisée:** {self.format_bytes(ram_used)}\n"
                f"**Disponible:** {self.format_bytes(ram_available)}\n"
                f"**Total:** {self.format_bytes(ram_total)}"
            ),
            inline=False
        )

        # Graphiques historiques
        history = await self.get_stats_history_from_db(hours=1)

        if history:
            cpu_values = [s.get('cpu_percent') for s in history if s.get('cpu_percent') is not None]
            ram_values = [s.get('ram_percent') for s in history if s.get('ram_percent') is not None]

            if cpu_values:
                embed.add_field(
                    name="📈 CPU (1h)",
                    value=self.create_ascii_graph(cpu_values),
                    inline=True
                )

            if ram_values:
                embed.add_field(
                    name="📈 RAM (1h)",
                    value=self.create_ascii_graph(ram_values),
                    inline=True
                )

        # Seuils d'alerte
        embed.add_field(
            name="⚠️ Seuils d'Alerte",
            value=(
                f"**CPU:** Warning {self.thresholds['cpu']['warning']}% | Critical {self.thresholds['cpu']['critical']}%\n"
                f"**RAM:** Warning {self.thresholds['ram']['warning']}% | Critical {self.thresholds['ram']['critical']}%"
            ),
            inline=False
        )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function pour charger le cog."""
    await bot.add_cog(MonitoringCog(bot))
