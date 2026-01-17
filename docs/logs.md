# Système de Logging

Guide complet du système de logs du projet Minecraft.

---

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Structure des fichiers](#structure-des-fichiers)
- [Logs Discord](#logs-discord)
- [Logs base de données](#logs-base-de-données)
- [Logs serveur Minecraft](#logs-serveur-minecraft)
- [Recherche et filtrage](#recherche-et-filtrage)
- [Export des logs](#export-des-logs)
- [Commandes /logs](#commandes-logs)
- [Configuration](#configuration)
- [Rétention et archivage](#rétention-et-archivage)

---

## Vue d'ensemble

Le système de logging centralise tous les événements des différents services.

### Sources de logs

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Minecraft  │     │     Bot      │     │     Web      │
│   Server     │     │   Discord    │     │  Dashboard   │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────┬───────┴────────────┬───────┘
                    │                    │
              ┌─────┴─────┐        ┌─────┴─────┐
              │  Fichiers │        │  Database │
              │   Logs    │        │   Logs    │
              └───────────┘        └───────────┘
```

### Niveaux de logs

| Niveau | Description | Couleur | Utilisation |
|--------|-------------|---------|-------------|
| `DEBUG` | Détails techniques | Gris | Développement |
| `INFO` | Informations générales | Bleu | Production |
| `WARNING` | Avertissements | Jaune | Attention requise |
| `ERROR` | Erreurs | Rouge | Problème à résoudre |
| `CRITICAL` | Erreurs critiques | Rouge foncé | Action immédiate |

---

## Structure des fichiers

### Organisation des dossiers

```
logs/
├── bot/
│   ├── 2024/
│   │   ├── 01/
│   │   │   ├── 2024-01-15.log
│   │   │   ├── 2024-01-16.log
│   │   │   └── ...
│   │   └── 02/
│   │       └── ...
│   └── current.log -> 2024/01/2024-01-16.log
├── minecraft/
│   ├── 2024/
│   │   └── 01/
│   │       ├── 2024-01-15.log
│   │       └── ...
│   └── current.log
├── web/
│   ├── 2024/
│   │   └── 01/
│   │       └── ...
│   └── current.log
└── combined/
    └── 2024/
        └── 01/
            └── ...
```

### Format des fichiers

**Nom du fichier :** `YYYY-MM-DD.log`

**Format d'une ligne :**

```
[2024-01-15 14:32:15.123] [INFO] [bot.commands] User#1234 executed /server status
```

Structure :
```
[timestamp] [level] [source] message
```

### Fichiers par service

| Service | Chemin | Contenu |
|---------|--------|---------|
| Bot | `logs/bot/` | Commandes, erreurs, connexions |
| Minecraft | `logs/minecraft/` | Console serveur, chat, événements |
| Web | `logs/web/` | Requêtes HTTP, auth, API |
| Combined | `logs/combined/` | Tous les logs agrégés |

---

## Logs Discord

### Événements loggués

| Événement | Niveau | Description |
|-----------|--------|-------------|
| Commande exécutée | INFO | Utilisateur + commande |
| Commande échouée | ERROR | Erreur + traceback |
| Bot connecté | INFO | Démarrage du bot |
| Bot déconnecté | WARNING | Déconnexion |
| Permission refusée | WARNING | Tentative non autorisée |
| Rate limit | WARNING | Limite Discord atteinte |

### Exemple de logs bot

```
[2024-01-15 14:30:00.000] [INFO] [bot.main] Bot connecté en tant que MinecraftBot#1234
[2024-01-15 14:30:01.000] [INFO] [bot.main] Connecté à 1 serveur(s)
[2024-01-15 14:30:02.000] [INFO] [bot.commands] Synchronisation des commandes slash...
[2024-01-15 14:30:05.000] [INFO] [bot.commands] 25 commandes synchronisées
[2024-01-15 14:32:15.123] [INFO] [bot.cogs.server] User:Steve#1234 Guild:123456 Command:/server status
[2024-01-15 14:32:15.456] [DEBUG] [bot.rcon] RCON connect to minecraft:25575
[2024-01-15 14:32:15.789] [DEBUG] [bot.rcon] RCON response: Server is running
[2024-01-15 14:35:42.000] [WARNING] [bot.cogs.server] User:Hacker#9999 Permission denied for /server stop
[2024-01-15 14:40:00.000] [ERROR] [bot.rcon] RCON connection timeout after 5s
Traceback (most recent call last):
  File "bot/utils/rcon.py", line 45, in connect
    await asyncio.wait_for(self._connect(), timeout=5)
asyncio.TimeoutError
```

### Configuration du logger Python

```python
# bot/utils/logger.py

import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

def setup_logger(name: str, level: str = "INFO"):
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Format
    formatter = logging.Formatter(
        '[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler avec rotation journalière
    today = datetime.now()
    log_dir = f"logs/bot/{today.year}/{today.month:02d}"
    os.makedirs(log_dir, exist_ok=True)

    file_handler = TimedRotatingFileHandler(
        filename=f"{log_dir}/{today.strftime('%Y-%m-%d')}.log",
        when='midnight',
        interval=1,
        backupCount=30
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
```

---

## Logs base de données

### Schéma de la table logs

```sql
CREATE TABLE logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(10) NOT NULL,
    source VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    user_id VARCHAR(20),
    guild_id VARCHAR(20),
    extra JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour les recherches rapides
CREATE INDEX idx_logs_timestamp ON logs(timestamp);
CREATE INDEX idx_logs_level ON logs(level);
CREATE INDEX idx_logs_source ON logs(source);
CREATE INDEX idx_logs_user_id ON logs(user_id);
```

### Types de logs stockés

| Source | Description | Rétention |
|--------|-------------|-----------|
| `command` | Commandes exécutées | 90 jours |
| `permission` | Vérifications de permission | 30 jours |
| `player` | Événements joueurs | 180 jours |
| `server` | Événements serveur | 365 jours |
| `error` | Erreurs | 30 jours |
| `audit` | Actions admin | Indéfini |

### Insertion de logs

```python
# bot/utils/db_logger.py

async def log_to_db(
    level: str,
    source: str,
    message: str,
    user_id: str = None,
    guild_id: str = None,
    extra: dict = None
):
    query = """
        INSERT INTO logs (level, source, message, user_id, guild_id, extra)
        VALUES ($1, $2, $3, $4, $5, $6)
    """
    await db.execute(query, level, source, message, user_id, guild_id, json.dumps(extra))
```

### Requêtes utiles

```sql
-- Logs des dernières 24 heures
SELECT * FROM logs
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- Erreurs par source
SELECT source, COUNT(*) as error_count
FROM logs
WHERE level = 'ERROR'
AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY source
ORDER BY error_count DESC;

-- Activité d'un utilisateur
SELECT timestamp, source, message
FROM logs
WHERE user_id = '123456789'
ORDER BY timestamp DESC
LIMIT 100;

-- Commandes les plus utilisées
SELECT
    message,
    COUNT(*) as usage_count
FROM logs
WHERE source = 'command'
AND timestamp > NOW() - INTERVAL '30 days'
GROUP BY message
ORDER BY usage_count DESC
LIMIT 20;
```

---

## Logs serveur Minecraft

### Sources de logs Minecraft

| Fichier | Contenu |
|---------|---------|
| `latest.log` | Log actuel du serveur |
| `debug.log` | Logs de debug détaillés |
| `crash-reports/` | Rapports de crash |

### Parser les logs Minecraft

```python
# bot/utils/minecraft_logs.py

import re
from datetime import datetime

LOG_PATTERN = r'\[(\d{2}:\d{2}:\d{2})\] \[([^/]+)/([A-Z]+)\]: (.+)'

def parse_minecraft_log(line: str):
    match = re.match(LOG_PATTERN, line)
    if match:
        return {
            'time': match.group(1),
            'thread': match.group(2),
            'level': match.group(3),
            'message': match.group(4)
        }
    return None

# Exemple de ligne :
# [14:32:15] [Server thread/INFO]: Steve joined the game
```

### Événements détectés

```python
# Patterns d'événements
PLAYER_JOIN = r'(\w+) joined the game'
PLAYER_LEAVE = r'(\w+) left the game'
PLAYER_DEATH = r'(\w+) (was|died|fell|drowned|burned|starved|suffocated|withered|was killed)'
PLAYER_CHAT = r'<(\w+)> (.+)'
ACHIEVEMENT = r'(\w+) has made the advancement \[(.+)\]'
SERVER_START = r'Done \([\d.]+s\)!'
SERVER_STOP = r'Stopping server'
```

### Intégration avec le bot

```python
# bot/cogs/log_watcher.py

import asyncio
import aiofiles

class LogWatcher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_path = "/data/logs/latest.log"
        self.running = False

    async def watch_logs(self):
        self.running = True
        async with aiofiles.open(self.log_path, 'r') as f:
            # Aller à la fin du fichier
            await f.seek(0, 2)

            while self.running:
                line = await f.readline()
                if line:
                    await self.process_log_line(line)
                else:
                    await asyncio.sleep(0.1)

    async def process_log_line(self, line: str):
        parsed = parse_minecraft_log(line)
        if not parsed:
            return

        # Détecter les événements
        if "joined the game" in parsed['message']:
            await self.on_player_join(parsed)
        elif "left the game" in parsed['message']:
            await self.on_player_leave(parsed)
        # ...etc
```

---

## Recherche et filtrage

### Via la base de données

```sql
-- Recherche par mot-clé
SELECT * FROM logs
WHERE message ILIKE '%error%'
ORDER BY timestamp DESC
LIMIT 50;

-- Filtrer par période
SELECT * FROM logs
WHERE timestamp BETWEEN '2024-01-15 00:00:00' AND '2024-01-15 23:59:59'
ORDER BY timestamp;

-- Filtrer par niveau
SELECT * FROM logs
WHERE level IN ('ERROR', 'CRITICAL')
AND timestamp > NOW() - INTERVAL '24 hours';

-- Recherche full-text (PostgreSQL)
SELECT * FROM logs
WHERE to_tsvector('french', message) @@ to_tsquery('french', 'connexion & echec');
```

### Via les fichiers

```bash
# Rechercher dans les logs du jour
grep -i "error" logs/bot/2024/01/2024-01-15.log

# Rechercher avec contexte
grep -B 2 -A 2 "CRITICAL" logs/bot/current.log

# Rechercher dans tous les logs
find logs/ -name "*.log" -exec grep -l "pattern" {} \;

# Compter les occurrences
grep -c "timeout" logs/bot/2024/01/*.log

# Logs en temps réel
tail -f logs/bot/current.log | grep --line-buffered "ERROR"
```

### Via le dashboard web

Le dashboard offre une interface de recherche :

```
┌─────────────────────────────────────────────────────────────┐
│  Recherche dans les logs                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Recherche : [________________________] [Rechercher]        │
│                                                             │
│  Filtres :                                                  │
│  Niveau : [Tous ▼]  Source : [Tous ▼]  Période : [24h ▼]  │
│                                                             │
│  [ ] Erreurs uniquement                                     │
│  [ ] Inclure les logs archivés                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Export des logs

### Export CSV

```python
# bot/utils/export.py

import csv
from io import StringIO

async def export_logs_csv(filters: dict) -> str:
    query = """
        SELECT timestamp, level, source, message, user_id
        FROM logs
        WHERE timestamp > $1
        ORDER BY timestamp DESC
    """
    rows = await db.fetch(query, filters.get('since'))

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Level', 'Source', 'Message', 'User ID'])

    for row in rows:
        writer.writerow([
            row['timestamp'].isoformat(),
            row['level'],
            row['source'],
            row['message'],
            row['user_id']
        ])

    return output.getvalue()
```

### Export JSON

```python
async def export_logs_json(filters: dict) -> str:
    query = """
        SELECT timestamp, level, source, message, user_id, extra
        FROM logs
        WHERE timestamp > $1
        ORDER BY timestamp DESC
    """
    rows = await db.fetch(query, filters.get('since'))

    logs = []
    for row in rows:
        logs.append({
            'timestamp': row['timestamp'].isoformat(),
            'level': row['level'],
            'source': row['source'],
            'message': row['message'],
            'user_id': row['user_id'],
            'extra': row['extra']
        })

    return json.dumps(logs, indent=2, ensure_ascii=False)
```

### Via commande bash

```bash
# Export simple
docker compose exec -T db psql -U minecraft_user -d minecraft_db \
    -c "COPY (SELECT * FROM logs WHERE timestamp > NOW() - INTERVAL '24 hours') TO STDOUT WITH CSV HEADER" \
    > logs_export.csv

# Export compressé
docker compose exec -T db pg_dump -U minecraft_user -t logs minecraft_db | gzip > logs_backup.sql.gz
```

---

## Commandes /logs

### `/logs view`

Affiche les logs récents dans Discord.

**Permission requise :** `ADMIN`

**Options :**

| Option | Description | Défaut |
|--------|-------------|--------|
| `lines` | Nombre de lignes | 20 |
| `level` | Niveau minimum | INFO |
| `source` | Source spécifique | all |

**Exemple :**

```
/logs view lines:50 level:error source:rcon
```

**Réponse :**

```
Logs (50 dernières lignes) - Filtre: ERROR, Source: rcon

[14:40:00] [ERROR] RCON connection timeout after 5s
[14:42:15] [ERROR] RCON authentication failed
[14:45:30] [ERROR] RCON command failed: connection reset

--- Fin des logs ---
```

### `/logs search`

Recherche dans les logs.

**Permission requise :** `ADMIN`

**Options :**

| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `query` | Terme de recherche | Oui |
| `period` | Période (1h, 24h, 7d) | Non (24h) |

**Exemple :**

```
/logs search query:permission denied period:7d
```

### `/logs export`

Exporte les logs en fichier.

**Permission requise :** `ADMIN`

**Options :**

| Option | Description | Défaut |
|--------|-------------|--------|
| `format` | csv, json, txt | csv |
| `period` | Période | 24h |

**Exemple :**

```
/logs export format:json period:7d
```

**Réponse :** Un fichier est envoyé en pièce jointe.

### `/logs stats`

Affiche les statistiques des logs.

**Permission requise :** `MODERATOR`

**Exemple :**

```
/logs stats
```

**Réponse :**

```
Statistiques des logs (7 derniers jours)

Total : 15,432 entrées

Par niveau :
  DEBUG    : 8,234 (53%)
  INFO     : 6,102 (40%)
  WARNING  :   823 (5%)
  ERROR    :   267 (2%)
  CRITICAL :     6 (<1%)

Top sources :
  1. bot.commands     : 4,521
  2. minecraft.events : 3,892
  3. bot.rcon         : 2,156
  4. web.api          : 1,843
  5. bot.permissions  :   892
```

---

## Configuration

### Variables d'environnement

```env
# Niveau de log global
LOG_LEVEL=info

# Rétention des logs (jours)
LOG_RETENTION_DAYS=30

# Taille max des fichiers de log
LOG_MAX_SIZE=10M

# Nombre de fichiers de rotation
LOG_BACKUP_COUNT=5

# Activer les logs dans la base de données
LOG_TO_DATABASE=true

# Activer les logs fichiers
LOG_TO_FILE=true
```

### Configuration par service

```yaml
# docker-compose.yml
services:
  bot:
    environment:
      LOG_LEVEL: ${LOG_LEVEL:-info}
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  minecraft:
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"
```

### Configuration Python détaillée

```python
# config/logging.py

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': '[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': 'DEBUG'
        },
        'file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'logs/bot/current.log',
            'when': 'midnight',
            'backupCount': 30,
            'formatter': 'detailed',
            'level': 'INFO'
        },
        'error_file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/bot/errors.log',
            'formatter': 'detailed',
            'level': 'ERROR'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO'
        },
        'bot.commands': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG'
        },
        'bot.rcon': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG'
        }
    }
}
```

---

## Rétention et archivage

### Politique de rétention

| Type de log | Fichiers | Base de données |
|-------------|----------|-----------------|
| Debug | 7 jours | Non stocké |
| Info | 30 jours | 90 jours |
| Warning | 90 jours | 180 jours |
| Error | 180 jours | 365 jours |
| Audit | 365 jours | Indéfini |

### Script de nettoyage

```bash
#!/bin/bash
# cleanup-logs.sh

LOG_DIR="./logs"

# Supprimer les logs de plus de 30 jours
find ${LOG_DIR} -name "*.log" -mtime +30 -delete

# Compresser les logs de plus de 7 jours
find ${LOG_DIR} -name "*.log" -mtime +7 -exec gzip {} \;

# Nettoyer la base de données
docker compose exec -T db psql -U minecraft_user -d minecraft_db << EOF
DELETE FROM logs WHERE timestamp < NOW() - INTERVAL '90 days' AND level = 'INFO';
DELETE FROM logs WHERE timestamp < NOW() - INTERVAL '30 days' AND level = 'DEBUG';
DELETE FROM logs WHERE timestamp < NOW() - INTERVAL '180 days' AND level = 'WARNING';
VACUUM ANALYZE logs;
EOF

echo "Nettoyage des logs terminé."
```

### Archivage

```bash
#!/bin/bash
# archive-logs.sh

ARCHIVE_DIR="./archives/logs"
MONTH=$(date -d "last month" +%Y-%m)

mkdir -p ${ARCHIVE_DIR}

# Archiver les logs du mois précédent
tar -czf ${ARCHIVE_DIR}/logs-${MONTH}.tar.gz ./logs/*/$(date -d "last month" +%Y)/$(date -d "last month" +%m)/

# Supprimer les fichiers archivés
rm -rf ./logs/*/$(date -d "last month" +%Y)/$(date -d "last month" +%m)/

echo "Logs du mois ${MONTH} archivés."
```

---

## Liens connexes

- [Configuration](configuration.md)
- [Commandes du bot](bot/commands.md)
- [Maintenance Docker](docker/maintenance.md)
- [Dépannage](troubleshooting.md)
