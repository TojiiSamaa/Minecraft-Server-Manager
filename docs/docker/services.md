# Services Docker

Description complete de tous les services Docker du projet.

---

## Table des matieres

- [Vue d'ensemble](#vue-densemble)
- [Service minecraft (NeoForge)](#service-minecraft-neoforge)
- [Service bot (Python)](#service-bot-python)
- [Service web (Next.js)](#service-web-nextjs)
- [Service db (PostgreSQL)](#service-db-postgresql)
- [Service redis](#service-redis)
- [Reseau et communication](#reseau-et-communication)
- [Volumes et persistance](#volumes-et-persistance)
- [Variables d'environnement](#variables-denvironnement)

---

## Vue d'ensemble

Le projet utilise Docker Compose pour orchestrer 5 services interconnectes.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Docker Network                             │
│                      (minecraft-network)                         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  minecraft   │  │     bot      │  │     web      │          │
│  │   NeoForge   │  │    Python    │  │   Next.js    │          │
│  │              │  │              │  │              │          │
│  │  Port: 25565 │  │  (interne)   │  │  Port: 3000  │          │
│  │  RCON: 25575 │  │              │  │              │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └────────────┬────┴────────┬────────┘                   │
│                      │             │                            │
│              ┌───────┴───────┐ ┌───┴───────────┐               │
│              │      db       │ │     redis     │               │
│              │  PostgreSQL   │ │               │               │
│              │  Port: 5432   │ │  Port: 6379   │               │
│              └───────────────┘ └───────────────┘               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Ports exposes vers l'hote :
  - 25565 : Minecraft (TCP/UDP)
  - 3000  : Dashboard Web (TCP)
  - 5432  : PostgreSQL (optionnel, dev uniquement)
```

### Fichier docker-compose.yml

```yaml
version: "3.9"

services:
  minecraft:
    # Serveur Minecraft NeoForge

  bot:
    # Bot Discord Python

  web:
    # Dashboard Next.js

  db:
    # Base de donnees PostgreSQL

  redis:
    # Cache Redis

networks:
  minecraft-network:
    driver: bridge

volumes:
  minecraft-data:
  postgres-data:
  redis-data:
```

---

## Service minecraft (NeoForge)

### Description

Serveur Minecraft NeoForge utilisant l'image `itzg/minecraft-server`.

### Configuration

```yaml
minecraft:
  image: itzg/minecraft-server:latest
  container_name: ${PROJECT_NAME:-minecraft}-minecraft
  restart: unless-stopped

  environment:
    # Type de serveur
    TYPE: NEOFORGE
    VERSION: ${MINECRAFT_VERSION:-1.20.4}
    EULA: "TRUE"

    # Memoire
    MEMORY: ${MINECRAFT_MEMORY_MAX:-4G}
    INIT_MEMORY: ${MINECRAFT_MEMORY_MIN:-2G}

    # RCON
    ENABLE_RCON: "true"
    RCON_PASSWORD: ${RCON_PASSWORD}
    RCON_PORT: 25575

    # Configuration du jeu
    SERVER_NAME: ${PROJECT_NAME:-Minecraft Server}
    MOTD: ${MINECRAFT_MOTD:-Welcome!}
    MAX_PLAYERS: ${MINECRAFT_MAX_PLAYERS:-20}
    DIFFICULTY: ${MINECRAFT_DIFFICULTY:-normal}
    GAMEMODE: ${MINECRAFT_GAMEMODE:-survival}
    ONLINE_MODE: ${MINECRAFT_ONLINE_MODE:-true}
    PVP: ${MINECRAFT_PVP:-true}
    VIEW_DISTANCE: ${MINECRAFT_VIEW_DISTANCE:-10}

    # Timezone
    TZ: ${TZ:-Europe/Paris}

  ports:
    - "${MINECRAFT_PORT:-25565}:25565"
    - "25575:25575"  # RCON (interne)

  volumes:
    - minecraft-data:/data
    - ./minecraft/mods:/data/mods:ro
    - ./minecraft/config:/data/config
    - ./minecraft/world:/data/world

  networks:
    - minecraft-network

  healthcheck:
    test: mc-health
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 120s
```

### Ports

| Port | Protocole | Description |
|------|-----------|-------------|
| 25565 | TCP/UDP | Connexion Minecraft |
| 25575 | TCP | RCON (console distante) |

### Volumes

| Volume | Chemin conteneur | Description |
|--------|------------------|-------------|
| `minecraft-data` | `/data` | Donnees du serveur |
| `./minecraft/mods` | `/data/mods` | Mods NeoForge |
| `./minecraft/config` | `/data/config` | Configuration |
| `./minecraft/world` | `/data/world` | Monde principal |

### Variables d'environnement

| Variable | Description | Defaut |
|----------|-------------|--------|
| `TYPE` | Type de serveur | `NEOFORGE` |
| `VERSION` | Version Minecraft | `1.20.4` |
| `MEMORY` | RAM maximale | `4G` |
| `RCON_PASSWORD` | Mot de passe RCON | Requis |
| `MAX_PLAYERS` | Joueurs max | `20` |

### Commandes utiles

```bash
# Voir les logs
docker compose logs -f minecraft

# Acceder a la console
docker compose exec minecraft rcon-cli

# Redemarrer le serveur
docker compose restart minecraft

# Arreter proprement
docker compose exec minecraft rcon-cli stop
```

---

## Service bot (Python)

### Description

Bot Discord ecrit en Python avec discord.py.

### Configuration

```yaml
bot:
  build:
    context: ./bot
    dockerfile: Dockerfile
  container_name: ${PROJECT_NAME:-minecraft}-bot
  restart: unless-stopped

  environment:
    # Discord
    DISCORD_TOKEN: ${DISCORD_TOKEN}
    DISCORD_GUILD_ID: ${DISCORD_GUILD_ID}
    DISCORD_CLIENT_ID: ${DISCORD_CLIENT_ID}
    DISCORD_ADMIN_ROLE_ID: ${DISCORD_ADMIN_ROLE_ID}
    DISCORD_MOD_ROLE_ID: ${DISCORD_MOD_ROLE_ID}

    # RCON
    RCON_HOST: minecraft
    RCON_PORT: 25575
    RCON_PASSWORD: ${RCON_PASSWORD}

    # Database
    DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}

    # Redis
    REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379

    # General
    TZ: ${TZ:-Europe/Paris}
    LOG_LEVEL: ${LOG_LEVEL:-info}

  volumes:
    - ./bot:/app
    - ./logs/bot:/app/logs

  networks:
    - minecraft-network

  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
    minecraft:
      condition: service_healthy
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Installation des dependances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code
COPY . .

# Point d'entree
CMD ["python", "main.py"]
```

### Dependances

Le bot attend que les services suivants soient prets :
- `db` (PostgreSQL)
- `redis`
- `minecraft`

### Volumes

| Volume | Chemin conteneur | Description |
|--------|------------------|-------------|
| `./bot` | `/app` | Code source |
| `./logs/bot` | `/app/logs` | Fichiers de logs |

### Commandes utiles

```bash
# Voir les logs
docker compose logs -f bot

# Redemarrer le bot
docker compose restart bot

# Executer une commande Python
docker compose exec bot python -c "print('Hello')"

# Acceder au shell
docker compose exec bot bash
```

---

## Service web (Next.js)

### Description

Dashboard web Next.js 14 avec authentification Discord OAuth.

### Configuration

```yaml
web:
  build:
    context: ./web
    dockerfile: Dockerfile
  container_name: ${PROJECT_NAME:-minecraft}-web
  restart: unless-stopped

  environment:
    # NextAuth
    NEXTAUTH_URL: ${NEXTAUTH_URL:-http://localhost:3000}
    NEXTAUTH_SECRET: ${NEXTAUTH_SECRET}

    # Discord OAuth
    DISCORD_CLIENT_ID: ${DISCORD_CLIENT_ID}
    DISCORD_CLIENT_SECRET: ${DISCORD_CLIENT_SECRET}

    # Database
    DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}

    # Redis
    REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379

    # API interne
    INTERNAL_API_KEY: ${INTERNAL_API_KEY}
    BOT_API_URL: http://bot:8080

    # General
    TZ: ${TZ:-Europe/Paris}
    NODE_ENV: ${NODE_ENV:-production}

  ports:
    - "${WEB_PORT:-3000}:3000"

  volumes:
    - ./web:/app
    - /app/node_modules
    - /app/.next

  networks:
    - minecraft-network

  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
```

### Dockerfile

```dockerfile
FROM node:20-alpine

WORKDIR /app

# Installation des dependances
COPY package*.json ./
RUN npm ci

# Copie du code
COPY . .

# Build
RUN npm run build

# Port
EXPOSE 3000

# Demarrage
CMD ["npm", "start"]
```

### Ports

| Port | Protocole | Description |
|------|-----------|-------------|
| 3000 | TCP | Interface web |

### Volumes

| Volume | Chemin conteneur | Description |
|--------|------------------|-------------|
| `./web` | `/app` | Code source |
| Anonyme | `/app/node_modules` | Dependances npm |
| Anonyme | `/app/.next` | Build Next.js |

### Commandes utiles

```bash
# Voir les logs
docker compose logs -f web

# Redemarrer
docker compose restart web

# Rebuild
docker compose build web
docker compose up -d web

# Acceder au shell
docker compose exec web sh
```

---

## Service db (PostgreSQL)

### Description

Base de donnees PostgreSQL 16 pour la persistance des donnees.

### Configuration

```yaml
db:
  image: postgres:16-alpine
  container_name: ${PROJECT_NAME:-minecraft}-db
  restart: unless-stopped

  environment:
    POSTGRES_DB: ${POSTGRES_DB:-minecraft_db}
    POSTGRES_USER: ${POSTGRES_USER:-minecraft_user}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    TZ: ${TZ:-Europe/Paris}

  volumes:
    - postgres-data:/var/lib/postgresql/data
    - ./docker/init-db.sql:/docker-entrypoint-initdb.d/init.sql:ro

  networks:
    - minecraft-network

  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-minecraft_user} -d ${POSTGRES_DB:-minecraft_db}"]
    interval: 10s
    timeout: 5s
    retries: 5
```

### Ports

| Port | Protocole | Description |
|------|-----------|-------------|
| 5432 | TCP | PostgreSQL (interne) |

> **Note :** Le port n'est pas expose par defaut pour des raisons de securite. Ajoutez `- "5432:5432"` dans `ports` pour un acces externe.

### Volumes

| Volume | Chemin conteneur | Description |
|--------|------------------|-------------|
| `postgres-data` | `/var/lib/postgresql/data` | Donnees |
| `./docker/init-db.sql` | `/docker-entrypoint-initdb.d/init.sql` | Script init |

### Script d'initialisation

```sql
-- docker/init-db.sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tables principales
CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    uuid UUID UNIQUE NOT NULL,
    username VARCHAR(16) NOT NULL,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    play_time INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(10) NOT NULL,
    source VARCHAR(50) NOT NULL,
    message TEXT NOT NULL
);

-- Index
CREATE INDEX idx_players_uuid ON players(uuid);
CREATE INDEX idx_logs_timestamp ON logs(timestamp);
```

### Commandes utiles

```bash
# Voir les logs
docker compose logs -f db

# Acceder a psql
docker compose exec db psql -U minecraft_user -d minecraft_db

# Backup
docker compose exec db pg_dump -U minecraft_user minecraft_db > backup.sql

# Restaurer
docker compose exec -T db psql -U minecraft_user minecraft_db < backup.sql
```

---

## Service redis

### Description

Cache Redis pour les sessions et le rate limiting.

### Configuration

```yaml
redis:
  image: redis:7-alpine
  container_name: ${PROJECT_NAME:-minecraft}-redis
  restart: unless-stopped

  command: >
    redis-server
    --requirepass ${REDIS_PASSWORD}
    --maxmemory ${REDIS_MAXMEMORY:-256mb}
    --maxmemory-policy ${REDIS_MAXMEMORY_POLICY:-allkeys-lru}
    --appendonly yes

  volumes:
    - redis-data:/data

  networks:
    - minecraft-network

  healthcheck:
    test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

### Ports

| Port | Protocole | Description |
|------|-----------|-------------|
| 6379 | TCP | Redis (interne) |

### Volumes

| Volume | Chemin conteneur | Description |
|--------|------------------|-------------|
| `redis-data` | `/data` | Donnees persistantes |

### Configuration memoire

| Parametre | Description | Defaut |
|-----------|-------------|--------|
| `maxmemory` | Memoire maximale | `256mb` |
| `maxmemory-policy` | Politique d'eviction | `allkeys-lru` |
| `appendonly` | Persistance AOF | `yes` |

### Commandes utiles

```bash
# Voir les logs
docker compose logs -f redis

# Acceder a redis-cli
docker compose exec redis redis-cli -a ${REDIS_PASSWORD}

# Voir les statistiques
docker compose exec redis redis-cli -a ${REDIS_PASSWORD} INFO

# Vider le cache
docker compose exec redis redis-cli -a ${REDIS_PASSWORD} FLUSHALL
```

---

## Reseau et communication

### Reseau Docker

Tous les services sont connectes au meme reseau bridge :

```yaml
networks:
  minecraft-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Communication inter-services

Les services communiquent via leurs noms de conteneur :

| Source | Destination | Port | Protocole |
|--------|-------------|------|-----------|
| bot | minecraft | 25575 | RCON |
| bot | db | 5432 | PostgreSQL |
| bot | redis | 6379 | Redis |
| web | db | 5432 | PostgreSQL |
| web | redis | 6379 | Redis |
| web | bot | 8080 | HTTP API |

### Exemple de connexion

```python
# Dans le bot Python
import asyncpg

conn = await asyncpg.connect(
    host='db',  # Nom du service
    port=5432,
    user='minecraft_user',
    password='password',
    database='minecraft_db'
)
```

---

## Volumes et persistance

### Volumes nommes

```yaml
volumes:
  minecraft-data:
    driver: local
  postgres-data:
    driver: local
  redis-data:
    driver: local
```

### Emplacement physique

```bash
# Linux
/var/lib/docker/volumes/

# Windows (Docker Desktop)
\\wsl$\docker-desktop-data\data\docker\volumes\
```

### Gestion des volumes

```bash
# Lister les volumes
docker volume ls

# Inspecter un volume
docker volume inspect minecraft-data

# Supprimer les volumes (ATTENTION !)
docker compose down -v

# Backup d'un volume
docker run --rm -v minecraft-data:/data -v $(pwd):/backup alpine tar czf /backup/minecraft-backup.tar.gz -C /data .
```

---

## Variables d'environnement

### Fichier .env complet

```env
# General
PROJECT_NAME=MonServeur
TZ=Europe/Paris

# Discord
DISCORD_TOKEN=xxx
DISCORD_GUILD_ID=xxx
DISCORD_CLIENT_ID=xxx
DISCORD_CLIENT_SECRET=xxx
DISCORD_ADMIN_ROLE_ID=xxx
DISCORD_MOD_ROLE_ID=xxx

# Minecraft
MINECRAFT_VERSION=1.20.4
MINECRAFT_MEMORY_MIN=2G
MINECRAFT_MEMORY_MAX=4G
MINECRAFT_PORT=25565
RCON_PASSWORD=xxx

# PostgreSQL
POSTGRES_DB=minecraft_db
POSTGRES_USER=minecraft_user
POSTGRES_PASSWORD=xxx

# Redis
REDIS_PASSWORD=xxx
REDIS_MAXMEMORY=256mb

# Web
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=xxx
WEB_PORT=3000
INTERNAL_API_KEY=xxx
```

---

## Liens connexes

- [Installation](../installation.md)
- [Configuration](../configuration.md)
- [Maintenance](maintenance.md)
- [Troubleshooting](../troubleshooting.md)
