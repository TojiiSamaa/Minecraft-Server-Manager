# Guide de Personnalisation

Guide pour étendre et personnaliser le projet Minecraft Server Manager.

---

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Ajouter une commande](#ajouter-une-commande)
- [Modifier les embeds](#modifier-les-embeds)
- [Ajouter une notification](#ajouter-une-notification)
- [Étendre l'API](#étendre-lapi)
- [Personnaliser le dashboard](#personnaliser-le-dashboard)
- [Créer un plugin](#créer-un-plugin)
- [Bonnes pratiques](#bonnes-pratiques)

---

## Vue d'ensemble

Le projet est conçu pour être facilement extensible. Cette section couvre les principales manières de le personnaliser.

### Structure du code

```
bot/
├── cogs/                  # Modules de commandes
│   ├── server.py         # Commandes serveur
│   ├── players.py        # Commandes joueurs
│   ├── rcon.py           # Commandes RCON
│   ├── notifications.py  # Commandes notifications
│   └── admin.py          # Commandes admin
├── utils/                 # Utilitaires
│   ├── embeds.py         # Constructeurs d'embeds
│   ├── permissions.py    # Système de permissions
│   └── rcon.py           # Client RCON
├── events/                # Gestionnaires d'événements
│   ├── player_events.py  # Événements joueurs
│   └── server_events.py  # Événements serveur
└── main.py               # Point d'entrée

web/
├── app/                   # Pages Next.js
├── components/            # Composants React
├── lib/                   # Bibliothèques
└── api/                   # Routes API
```

---

## Ajouter une commande

### Étape 1 : Créer le fichier ou modifier un cog existant

```python
# bot/cogs/custom.py

import discord
from discord import app_commands
from discord.ext import commands
from utils.permissions import require_permission, PermissionLevel
from utils.embeds import create_embed

class CustomCommands(commands.Cog):
    """Commandes personnalisées"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="hello", description="Dit bonjour")
    async def hello(self, interaction: discord.Interaction):
        """Commande simple qui dit bonjour"""
        await interaction.response.send_message(f"Bonjour {interaction.user.mention} !")

    @app_commands.command(name="ping", description="Affiche la latence du bot")
    async def ping(self, interaction: discord.Interaction):
        """Affiche la latence"""
        latency = round(self.bot.latency * 1000)

        embed = create_embed(
            title="Pong !",
            description=f"Latence : **{latency}ms**",
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed)


# Fonction de setup requise
async def setup(bot: commands.Bot):
    await bot.add_cog(CustomCommands(bot))
```

### Étape 2 : Charger le cog

```python
# bot/main.py

INITIAL_EXTENSIONS = [
    'cogs.server',
    'cogs.players',
    'cogs.rcon',
    'cogs.notifications',
    'cogs.admin',
    'cogs.custom',  # Ajouter votre cog
]

async def load_extensions():
    for ext in INITIAL_EXTENSIONS:
        await bot.load_extension(ext)
```

### Étape 3 : Ajouter des permissions

```python
# Commande avec permission requise
@app_commands.command(name="secret", description="Commande secrète")
@require_permission(PermissionLevel.ADMIN)
async def secret_command(self, interaction: discord.Interaction):
    await interaction.response.send_message("Ceci est secret !", ephemeral=True)
```

### Étape 4 : Ajouter des paramètres

```python
@app_commands.command(name="say", description="Fait parler le bot")
@app_commands.describe(
    message="Le message à envoyer",
    channel="Le channel cible (optionnel)"
)
@require_permission(PermissionLevel.MODERATOR)
async def say(
    self,
    interaction: discord.Interaction,
    message: str,
    channel: discord.TextChannel = None
):
    target = channel or interaction.channel
    await target.send(message)
    await interaction.response.send_message("Message envoyé !", ephemeral=True)
```

### Étape 5 : Ajouter des choix prédéfinis

```python
from discord.app_commands import Choice

@app_commands.command(name="color", description="Choisir une couleur")
@app_commands.describe(color="La couleur à choisir")
@app_commands.choices(color=[
    Choice(name="Rouge", value="red"),
    Choice(name="Vert", value="green"),
    Choice(name="Bleu", value="blue")
])
async def color_command(
    self,
    interaction: discord.Interaction,
    color: Choice[str]
):
    await interaction.response.send_message(f"Vous avez choisi : {color.name}")
```

### Étape 6 : Synchroniser les commandes

```bash
# Redémarrer le bot ou utiliser /admin sync
docker compose restart bot
```

---

## Modifier les embeds

### Structure d'un embed

```python
# bot/utils/embeds.py

import discord
from datetime import datetime

def create_embed(
    title: str = None,
    description: str = None,
    color: discord.Color = None,
    thumbnail: str = None,
    image: str = None,
    footer: str = None,
    fields: list = None,
    author: dict = None,
    timestamp: bool = True
) -> discord.Embed:
    """Crée un embed standardisé"""

    embed = discord.Embed(
        title=title,
        description=description,
        color=color or discord.Color.blue()
    )

    if timestamp:
        embed.timestamp = datetime.utcnow()

    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    if image:
        embed.set_image(url=image)

    if footer:
        embed.set_footer(text=footer)

    if author:
        embed.set_author(
            name=author.get('name'),
            icon_url=author.get('icon_url'),
            url=author.get('url')
        )

    if fields:
        for field in fields:
            embed.add_field(
                name=field['name'],
                value=field['value'],
                inline=field.get('inline', False)
            )

    return embed
```

### Embeds prédéfinis

```python
# bot/utils/embeds.py

# Couleurs standardisées
class Colors:
    SUCCESS = discord.Color.green()
    ERROR = discord.Color.red()
    WARNING = discord.Color.orange()
    INFO = discord.Color.blue()
    MINECRAFT = discord.Color.from_str("#5D8731")


def success_embed(message: str) -> discord.Embed:
    """Embed de succès"""
    return create_embed(
        title="Succès",
        description=message,
        color=Colors.SUCCESS
    )


def error_embed(message: str) -> discord.Embed:
    """Embed d'erreur"""
    return create_embed(
        title="Erreur",
        description=message,
        color=Colors.ERROR
    )


def server_status_embed(status: dict) -> discord.Embed:
    """Embed de statut serveur"""
    online = status.get('online', False)

    return create_embed(
        title="Statut du Serveur",
        description=f"**{'En ligne' if online else 'Hors ligne'}**",
        color=Colors.SUCCESS if online else Colors.ERROR,
        thumbnail="https://example.com/minecraft-icon.png",
        fields=[
            {"name": "Version", "value": status.get('version', 'N/A'), "inline": True},
            {"name": "Joueurs", "value": f"{status.get('players', 0)}/{status.get('max_players', 20)}", "inline": True},
            {"name": "TPS", "value": str(status.get('tps', 'N/A')), "inline": True},
            {"name": "Mémoire", "value": f"{status.get('ram_used', 0)} MB", "inline": True},
            {"name": "Uptime", "value": status.get('uptime', 'N/A'), "inline": True}
        ],
        footer="Dernière mise à jour"
    )
```

### Personnaliser les couleurs

```python
# config/colors.py

EMBED_COLORS = {
    'player_join': 0x2ecc71,     # Vert
    'player_leave': 0xe74c3c,    # Rouge
    'player_death': 0x2c3e50,    # Noir
    'achievement': 0xf39c12,     # Or
    'server_start': 0x27ae60,    # Vert foncé
    'server_stop': 0xe67e22,     # Orange
    'alert': 0xc0392b,           # Rouge foncé
}

def get_color(event_type: str) -> int:
    return EMBED_COLORS.get(event_type, 0x3498db)
```

### Ajouter des images dynamiques

```python
def get_player_head(username: str, size: int = 64) -> str:
    """URL de la tête du joueur via Crafatar"""
    return f"https://crafatar.com/avatars/{username}?size={size}&overlay"


def get_player_body(username: str) -> str:
    """URL du corps complet du joueur"""
    return f"https://crafatar.com/renders/body/{username}?overlay"
```

---

## Ajouter une notification

### Étape 1 : Définir le type de notification

```python
# bot/notifications/types.py

from enum import Enum

class NotificationType(Enum):
    PLAYER_JOIN = "player_join"
    PLAYER_LEAVE = "player_leave"
    PLAYER_DEATH = "player_death"
    PLAYER_ACHIEVEMENT = "player_achievement"
    SERVER_START = "server_start"
    SERVER_STOP = "server_stop"
    PERFORMANCE_ALERT = "performance_alert"
    # Ajouter votre nouveau type
    PLAYER_CHAT = "player_chat"
    CUSTOM_EVENT = "custom_event"
```

### Étape 2 : Créer le handler de notification

```python
# bot/notifications/handlers/chat.py

from utils.embeds import create_embed
from notifications.base import NotificationHandler

class ChatNotificationHandler(NotificationHandler):
    """Gère les notifications de chat"""

    notification_type = "player_chat"

    async def create_embed(self, data: dict) -> discord.Embed:
        return create_embed(
            title="Message dans le chat",
            description=f"**{data['player']}**: {data['message']}",
            color=discord.Color.blue(),
            thumbnail=f"https://crafatar.com/avatars/{data['player']}?size=64"
        )

    async def should_notify(self, data: dict) -> bool:
        # Ne pas notifier les messages de commandes
        if data['message'].startswith('/'):
            return False
        return True
```

### Étape 3 : Enregistrer le handler

```python
# bot/notifications/__init__.py

from .handlers.chat import ChatNotificationHandler

NOTIFICATION_HANDLERS = {
    'player_join': PlayerJoinHandler,
    'player_leave': PlayerLeaveHandler,
    'player_death': PlayerDeathHandler,
    'player_chat': ChatNotificationHandler,  # Nouveau
    # ...
}
```

### Étape 4 : Déclencher la notification

```python
# bot/events/player_events.py

async def on_player_chat(player: str, message: str):
    """Appelé quand un joueur écrit dans le chat"""
    await notification_manager.send(
        notification_type='player_chat',
        data={
            'player': player,
            'message': message,
            'timestamp': datetime.utcnow()
        }
    )
```

### Étape 5 : Ajouter la configuration

```python
# Ajouter à la commande /notifications configure
NOTIFICATION_TYPES = [
    # ...existants...
    {
        'value': 'player_chat',
        'name': 'Message chat',
        'description': 'Notification quand un joueur écrit dans le chat'
    }
]
```

---

## Étendre l'API

### Structure de l'API

```
web/
├── app/
│   └── api/
│       ├── server/
│       │   └── route.ts
│       ├── players/
│       │   └── route.ts
│       └── custom/          # Votre nouveau endpoint
│           └── route.ts
```

### Créer un nouveau endpoint

```typescript
// web/app/api/custom/stats/route.ts

import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { db } from '@/lib/db';

// GET /api/custom/stats
export async function GET(request: NextRequest) {
    // Vérifier l'authentification
    const session = await getServerSession(authOptions);
    if (!session) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    try {
        // Récupérer les statistiques
        const stats = await db.query(`
            SELECT
                COUNT(*) as total_commands,
                COUNT(DISTINCT user_id) as unique_users
            FROM logs
            WHERE source = 'command'
            AND timestamp > NOW() - INTERVAL '24 hours'
        `);

        return NextResponse.json({
            success: true,
            data: stats.rows[0]
        });
    } catch (error) {
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
}

// POST /api/custom/stats
export async function POST(request: NextRequest) {
    const session = await getServerSession(authOptions);
    if (!session) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    try {
        const body = await request.json();

        // Traiter les données
        // ...

        return NextResponse.json({ success: true });
    } catch (error) {
        return NextResponse.json(
            { error: 'Invalid request' },
            { status: 400 }
        );
    }
}
```

### Middleware d'authentification

```typescript
// web/lib/api-auth.ts

import { NextRequest, NextResponse } from 'next/server';

export async function withAuth(
    request: NextRequest,
    handler: (req: NextRequest, session: any) => Promise<NextResponse>
) {
    const apiKey = request.headers.get('Authorization')?.replace('Bearer ', '');

    if (!apiKey) {
        return NextResponse.json({ error: 'Missing API key' }, { status: 401 });
    }

    // Vérifier la clé API
    const session = await validateApiKey(apiKey);
    if (!session) {
        return NextResponse.json({ error: 'Invalid API key' }, { status: 401 });
    }

    return handler(request, session);
}
```

### Utiliser le middleware

```typescript
// web/app/api/custom/protected/route.ts

import { withAuth } from '@/lib/api-auth';

export async function GET(request: NextRequest) {
    return withAuth(request, async (req, session) => {
        // Code protégé
        return NextResponse.json({ user: session.user });
    });
}
```

---

## Personnaliser le dashboard

### Ajouter une page

```typescript
// web/app/custom/page.tsx

import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { redirect } from 'next/navigation';
import CustomDashboard from '@/components/custom/CustomDashboard';

export default async function CustomPage() {
    const session = await getServerSession(authOptions);

    if (!session) {
        redirect('/login');
    }

    return (
        <div className="container mx-auto py-6">
            <h1 className="text-2xl font-bold mb-6">Page Personnalisée</h1>
            <CustomDashboard />
        </div>
    );
}
```

### Créer un composant

```typescript
// web/components/custom/CustomDashboard.tsx

'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function CustomDashboard() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('/api/custom/stats')
            .then(res => res.json())
            .then(data => {
                setData(data);
                setLoading(false);
            });
    }, []);

    if (loading) {
        return <div>Chargement...</div>;
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
                <CardHeader>
                    <CardTitle>Statistiques</CardTitle>
                </CardHeader>
                <CardContent>
                    <p>Total commandes: {data?.total_commands}</p>
                    <p>Utilisateurs uniques: {data?.unique_users}</p>
                </CardContent>
            </Card>
        </div>
    );
}
```

### Ajouter au menu de navigation

```typescript
// web/components/layout/Navigation.tsx

const menuItems = [
    { name: 'Dashboard', href: '/', icon: HomeIcon },
    { name: 'Serveur', href: '/server', icon: ServerIcon },
    { name: 'Joueurs', href: '/players', icon: UsersIcon },
    { name: 'Console', href: '/console', icon: TerminalIcon },
    { name: 'Backups', href: '/backups', icon: ArchiveIcon },
    { name: 'Custom', href: '/custom', icon: StarIcon },  // Nouveau
];
```

---

## Créer un plugin

### Structure d'un plugin

```
plugins/
└── my-plugin/
    ├── __init__.py
    ├── plugin.json
    ├── cog.py
    └── README.md
```

### Fichier de configuration

```json
// plugins/my-plugin/plugin.json
{
    "name": "My Plugin",
    "version": "1.0.0",
    "description": "Mon plugin personnalisé",
    "author": "VotreNom",
    "dependencies": [],
    "cog": "cog.py"
}
```

### Code du plugin

```python
# plugins/my-plugin/cog.py

import discord
from discord import app_commands
from discord.ext import commands

class MyPlugin(commands.Cog):
    """Mon plugin personnalisé"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="myplugin", description="Commande de mon plugin")
    async def my_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello from my plugin!")


async def setup(bot: commands.Bot):
    await bot.add_cog(MyPlugin(bot))
```

### Chargeur de plugins

```python
# bot/utils/plugins.py

import json
import os
from pathlib import Path

async def load_plugins(bot):
    """Charge tous les plugins activés"""
    plugins_dir = Path("plugins")

    if not plugins_dir.exists():
        return

    for plugin_dir in plugins_dir.iterdir():
        if not plugin_dir.is_dir():
            continue

        config_file = plugin_dir / "plugin.json"
        if not config_file.exists():
            continue

        with open(config_file) as f:
            config = json.load(f)

        # Charger le cog
        cog_path = f"plugins.{plugin_dir.name}.{config['cog'].replace('.py', '')}"
        try:
            await bot.load_extension(cog_path)
            print(f"Plugin chargé : {config['name']} v{config['version']}")
        except Exception as e:
            print(f"Erreur chargement plugin {config['name']}: {e}")
```

---

## Bonnes pratiques

### Organisation du code

```python
# Bonne pratique : séparer la logique
class ServerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rcon = RconClient()
        self.db = Database()

    @app_commands.command(name="status")
    async def status(self, interaction: discord.Interaction):
        # Utiliser des services séparés
        status = await self.rcon.get_status()
        embed = ServerEmbeds.status(status)
        await interaction.response.send_message(embed=embed)
```

### Gestion des erreurs

```python
# Gestionnaire d'erreurs global
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "Vous n'avez pas la permission d'utiliser cette commande.",
            ephemeral=True
        )
    elif isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"Commande en cooldown. Réessayez dans {error.retry_after:.1f}s",
            ephemeral=True
        )
    else:
        logger.error(f"Erreur commande: {error}")
        await interaction.response.send_message(
            "Une erreur est survenue.",
            ephemeral=True
        )
```

### Tests

```python
# tests/test_commands.py

import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_status_command():
    bot = MagicMock()
    cog = ServerCommands(bot)

    interaction = AsyncMock()
    interaction.response.send_message = AsyncMock()

    await cog.status(interaction)

    interaction.response.send_message.assert_called_once()
```

### Documentation

```python
class ServerCommands(commands.Cog):
    """
    Commandes de gestion du serveur Minecraft.

    Attributes:
        bot: Instance du bot Discord
        rcon: Client RCON pour communiquer avec Minecraft

    Commands:
        /server status - Affiche le statut du serveur
        /server start - Démarre le serveur
        /server stop - Arrête le serveur
    """
```

---

## Liens connexes

- [Commandes du bot](bot/commands.md)
- [Notifications](bot/notifications.md)
- [API REST](web/dashboard.md#api-rest)
- [Configuration](configuration.md)
