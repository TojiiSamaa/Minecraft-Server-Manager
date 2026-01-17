# Guide de configuration

Ce guide detaille toutes les variables d'environnement disponibles et leur utilisation.

---

## Table des matieres

- [Structure du fichier .env](#structure-du-fichier-env)
- [Variables generales](#variables-generales)
- [Configuration Discord](#configuration-discord)
- [Configuration Minecraft](#configuration-minecraft)
- [Configuration PostgreSQL](#configuration-postgresql)
- [Configuration Redis](#configuration-redis)
- [Configuration Web/NextAuth](#configuration-webnextauth)
- [Configuration Backup](#configuration-backup)
- [Configuration Monitoring](#configuration-monitoring)
- [Exemple complet commente](#exemple-complet-commente)
- [Configuration avancee](#configuration-avancee)

---

## Structure du fichier .env

Le fichier `.env` se trouve a la racine du projet et contient toutes les configurations sensibles.

> **ATTENTION** : Ne jamais commiter le fichier `.env` dans Git !

---

## Variables generales

| Variable | Description | Valeurs possibles | Defaut |
|----------|-------------|-------------------|--------|
| `PROJECT_NAME` | Nom du projet | Chaine de caracteres | `MinecraftBot` |
| `NODE_ENV` | Environnement d'execution | `development`, `staging`, `production` | `production` |
| `TZ` | Fuseau horaire | Format `Region/City` | `Europe/Paris` |
| `LOG_LEVEL` | Niveau de log | `debug`, `info`, `warn`, `error` | `info` |
| `DOMAIN` | Domaine principal | URL ou domaine | `localhost` |

### Exemple

```env
PROJECT_NAME=MonServeur
NODE_ENV=production
TZ=Europe/Paris
LOG_LEVEL=info
DOMAIN=monserveur.fr
```

---

## Configuration Discord

### Variables requises

| Variable | Description | Ou trouver |
|----------|-------------|------------|
| `DISCORD_TOKEN` | Token du bot | Developer Portal > Bot > Token |
| `DISCORD_GUILD_ID` | ID du serveur principal | Clic droit sur le serveur |
| `DISCORD_CLIENT_ID` | ID de l'application | Developer Portal > General |
| `DISCORD_CLIENT_SECRET` | Secret OAuth2 | Developer Portal > OAuth2 |

### Variables optionnelles

| Variable | Description | Defaut |
|----------|-------------|--------|
| `DISCORD_PREFIX` | Prefixe des commandes textuelles | `!` |
| `DISCORD_ADMIN_ROLE_ID` | ID du role administrateur | - |
| `DISCORD_MOD_ROLE_ID` | ID du role moderateur | - |
| `DISCORD_LOG_CHANNEL_ID` | Channel pour les logs du bot | - |
| `DISCORD_STATUS_CHANNEL_ID` | Channel pour le statut serveur | - |
| `DISCORD_CHAT_CHANNEL_ID` | Channel pour le bridge chat | - |

### Exemple

```env
# Discord - Configuration requise
DISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.XXXXXX.XXXXXXXXXXXXXXXXXXXXXXXX
DISCORD_GUILD_ID=123456789012345678
DISCORD_CLIENT_ID=123456789012345678
DISCORD_CLIENT_SECRET=abcdefghijklmnopqrstuvwxyz123456

# Discord - Roles
DISCORD_ADMIN_ROLE_ID=123456789012345678
DISCORD_MOD_ROLE_ID=123456789012345678

# Discord - Channels
DISCORD_LOG_CHANNEL_ID=123456789012345678
DISCORD_STATUS_CHANNEL_ID=123456789012345678
DISCORD_CHAT_CHANNEL_ID=123456789012345678
DISCORD_PREFIX=!
```

---

## Configuration Minecraft

### Serveur

| Variable | Description | Valeurs | Defaut |
|----------|-------------|---------|--------|
| `MINECRAFT_VERSION` | Version du serveur | `1.20.4`, `1.21`, `latest` | `1.20.4` |
| `MINECRAFT_TYPE` | Type de serveur | `VANILLA`, `PAPER`, `SPIGOT`, `FABRIC`, `FORGE`, `NEOFORGE` | `PAPER` |
| `MINECRAFT_PORT` | Port du serveur | 1-65535 | `25565` |
| `MINECRAFT_MEMORY_MIN` | RAM minimale | `1G`, `2G`, etc. | `2G` |
| `MINECRAFT_MEMORY_MAX` | RAM maximale | `4G`, `8G`, etc. | `4G` |
| `MINECRAFT_MAX_PLAYERS` | Nombre max de joueurs | 1-999 | `20` |

### RCON (Remote Console)

| Variable | Description | Defaut |
|----------|-------------|--------|
| `RCON_HOST` | Hote RCON (nom du conteneur) | `minecraft` |
| `RCON_PORT` | Port RCON | `25575` |
| `RCON_PASSWORD` | Mot de passe RCON | Genere automatiquement |
| `RCON_TIMEOUT` | Timeout en secondes | `5.0` |

### Parametres du jeu

| Variable | Description | Valeurs | Defaut |
|----------|-------------|---------|--------|
| `MINECRAFT_MOTD` | Message du jour | Texte | `Welcome!` |
| `MINECRAFT_GAMEMODE` | Mode de jeu | `survival`, `creative`, `adventure`, `spectator` | `survival` |
| `MINECRAFT_DIFFICULTY` | Difficulte | `peaceful`, `easy`, `normal`, `hard` | `normal` |
| `MINECRAFT_ONLINE_MODE` | Verification Mojang | `true`, `false` | `true` |
| `MINECRAFT_PVP` | Combat entre joueurs | `true`, `false` | `true` |
| `MINECRAFT_VIEW_DISTANCE` | Distance de rendu (chunks) | 2-32 | `10` |

### Exemple

```env
# Minecraft Server
MINECRAFT_VERSION=1.20.4
MINECRAFT_TYPE=NEOFORGE
MINECRAFT_PORT=25565
MINECRAFT_MEMORY_MIN=2G
MINECRAFT_MEMORY_MAX=4G
MINECRAFT_MAX_PLAYERS=20

# RCON
RCON_HOST=minecraft
RCON_PORT=25575
RCON_PASSWORD=VotreMotDePasseSecurise123

# Game Settings
MINECRAFT_MOTD=Bienvenue sur MonServeur!
MINECRAFT_GAMEMODE=survival
MINECRAFT_DIFFICULTY=normal
MINECRAFT_ONLINE_MODE=true
MINECRAFT_PVP=true
MINECRAFT_VIEW_DISTANCE=10
```

---

## Configuration PostgreSQL

| Variable | Description | Defaut |
|----------|-------------|--------|
| `POSTGRES_HOST` | Hote (nom du conteneur) | `db` |
| `POSTGRES_PORT` | Port | `5432` |
| `POSTGRES_DB` | Nom de la base | `minecraft_db` |
| `POSTGRES_USER` | Utilisateur | `minecraft_user` |
| `POSTGRES_PASSWORD` | Mot de passe | Genere automatiquement |
| `DATABASE_URL` | URL complete | Auto-construite |
| `POSTGRES_MAX_CONNECTIONS` | Connexions max | `100` |

### Exemple

```env
# PostgreSQL
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=minecraft_db
POSTGRES_USER=minecraft_user
POSTGRES_PASSWORD=MotDePassePostgres123
DATABASE_URL=postgresql://minecraft_user:MotDePassePostgres123@db:5432/minecraft_db
```

---

## Configuration Redis

| Variable | Description | Defaut |
|----------|-------------|--------|
| `REDIS_HOST` | Hote (nom du conteneur) | `redis` |
| `REDIS_PORT` | Port | `6379` |
| `REDIS_PASSWORD` | Mot de passe | Genere automatiquement |
| `REDIS_URL` | URL complete | Auto-construite |
| `REDIS_MAXMEMORY` | Memoire maximale | `256mb` |
| `REDIS_MAXMEMORY_POLICY` | Politique d'eviction | `allkeys-lru` |

### Exemple

```env
# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=MotDePasseRedis123
REDIS_URL=redis://:MotDePasseRedis123@redis:6379
REDIS_MAXMEMORY=256mb
```

---

## Configuration Web/NextAuth

| Variable | Description | Exemple |
|----------|-------------|---------|
| `NEXTAUTH_URL` | URL du panel web | `http://localhost:3000` |
| `NEXTAUTH_SECRET` | Secret pour les sessions | Genere avec `openssl rand -base64 32` |
| `WEB_PORT` | Port du panel | `3000` |
| `SESSION_MAX_AGE` | Duree de session (secondes) | `604800` (7 jours) |
| `INTERNAL_API_KEY` | Cle API interne | Genere automatiquement |

### Exemple

```env
# Web / NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=VotreSecretBase64TresLong==
WEB_PORT=3000
SESSION_MAX_AGE=604800
INTERNAL_API_KEY=abcdef1234567890abcdef1234567890
```

---

## Configuration Backup

| Variable | Description | Defaut |
|----------|-------------|--------|
| `BACKUP_ENABLED` | Activer les backups | `true` |
| `BACKUP_INTERVAL` | Intervalle en heures | `6` |
| `BACKUP_RETENTION` | Nombre de backups a garder | `10` |
| `BACKUP_PATH` | Chemin de stockage | `./backups` |
| `BACKUP_COMPRESSION` | Compresser les backups | `true` |
| `BACKUP_INCLUDE_DATABASE` | Inclure la BDD | `true` |
| `BACKUP_DISCORD_NOTIFY` | Notification Discord | `true` |

### Backup distant (optionnel)

| Variable | Description |
|----------|-------------|
| `BACKUP_REMOTE_TYPE` | `s3`, `gcs`, `azure`, `none` |
| `BACKUP_REMOTE_BUCKET` | Nom du bucket |
| `BACKUP_REMOTE_REGION` | Region cloud |
| `BACKUP_REMOTE_ACCESS_KEY` | Cle d'acces |
| `BACKUP_REMOTE_SECRET_KEY` | Cle secrete |

### Exemple

```env
# Backups
BACKUP_ENABLED=true
BACKUP_INTERVAL=6
BACKUP_RETENTION=10
BACKUP_PATH=./backups
BACKUP_COMPRESSION=true
BACKUP_INCLUDE_DATABASE=true
BACKUP_DISCORD_NOTIFY=true
```

---

## Configuration Monitoring

### Seuils d'alerte

| Variable | Description | Defaut |
|----------|-------------|--------|
| `MONITORING_ENABLED` | Activer le monitoring | `true` |
| `MONITORING_INTERVAL` | Intervalle (secondes) | `30` |
| `ALERT_TPS_WARNING` | Seuil TPS warning | `18` |
| `ALERT_TPS_CRITICAL` | Seuil TPS critique | `15` |
| `ALERT_RAM_WARNING` | Seuil RAM warning (%) | `80` |
| `ALERT_RAM_CRITICAL` | Seuil RAM critique (%) | `90` |
| `ALERT_CPU_WARNING` | Seuil CPU warning (%) | `80` |
| `ALERT_CPU_CRITICAL` | Seuil CPU critique (%) | `95` |

### Exemple

```env
# Monitoring
MONITORING_ENABLED=true
MONITORING_INTERVAL=30
ALERT_TPS_WARNING=18
ALERT_TPS_CRITICAL=15
ALERT_RAM_WARNING=80
ALERT_RAM_CRITICAL=90
ALERT_CPU_WARNING=80
ALERT_CPU_CRITICAL=95
MONITORING_ALERT_CHANNEL_ID=123456789012345678
```

---

## Exemple complet commente

```env
# ============================================================================
# CONFIGURATION COMPLETE DU PROJET
# ============================================================================

# ----------------------------------------------------------------------------
# SECTION 1: GENERAL
# ----------------------------------------------------------------------------

# Nom du projet (utilise pour les conteneurs Docker, logs, etc.)
PROJECT_NAME=MonServeur

# Environnement d'execution
# development: logs verbeux, hot-reload active
# production: optimisations activees, logs minimaux
NODE_ENV=production

# Fuseau horaire du serveur
TZ=Europe/Paris

# Niveau de log global
LOG_LEVEL=info

# ----------------------------------------------------------------------------
# SECTION 2: DISCORD
# ----------------------------------------------------------------------------

# Token d'authentification du bot Discord
# Obtenir sur: https://discord.com/developers/applications
# ATTENTION: Ne jamais partager ce token !
DISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.XXXXXX.XXXXXXXXXXXXXXXXXXXXXXXX

# ID du serveur Discord principal (Guild ID)
DISCORD_GUILD_ID=123456789012345678

# ID de l'application Discord (Client ID)
DISCORD_CLIENT_ID=123456789012345678

# Secret client pour OAuth2
DISCORD_CLIENT_SECRET=abcdefghijklmnopqrstuvwxyz123456

# ID du role administrateur
DISCORD_ADMIN_ROLE_ID=123456789012345678

# ID du role moderateur
DISCORD_MOD_ROLE_ID=123456789012345678

# Prefixe des commandes textuelles
DISCORD_PREFIX=!

# Channels Discord
DISCORD_LOG_CHANNEL_ID=123456789012345678
DISCORD_STATUS_CHANNEL_ID=123456789012345678
DISCORD_CHAT_CHANNEL_ID=123456789012345678

# ----------------------------------------------------------------------------
# SECTION 3: MINECRAFT
# ----------------------------------------------------------------------------

# Version du serveur Minecraft
MINECRAFT_VERSION=1.20.4

# Type de serveur (VANILLA, PAPER, SPIGOT, FABRIC, FORGE, NEOFORGE)
MINECRAFT_TYPE=NEOFORGE

# Configuration RCON
RCON_HOST=minecraft
RCON_PORT=25575
RCON_PASSWORD=MotDePasseRCON123456789

# Port du serveur
MINECRAFT_PORT=25565

# Memoire RAM
MINECRAFT_MEMORY_MIN=2G
MINECRAFT_MEMORY_MAX=4G

# Parametres du jeu
MINECRAFT_MAX_PLAYERS=20
MINECRAFT_MOTD=Bienvenue sur MonServeur!
MINECRAFT_GAMEMODE=survival
MINECRAFT_DIFFICULTY=normal
MINECRAFT_ONLINE_MODE=true

# ----------------------------------------------------------------------------
# SECTION 4: POSTGRESQL
# ----------------------------------------------------------------------------

POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=minecraft_db
POSTGRES_USER=minecraft_user
POSTGRES_PASSWORD=MotDePassePostgres123456789
DATABASE_URL=postgresql://minecraft_user:MotDePassePostgres123456789@db:5432/minecraft_db

# ----------------------------------------------------------------------------
# SECTION 5: REDIS
# ----------------------------------------------------------------------------

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=MotDePasseRedis123456789
REDIS_URL=redis://:MotDePasseRedis123456789@redis:6379
REDIS_MAXMEMORY=256mb

# ----------------------------------------------------------------------------
# SECTION 6: WEB
# ----------------------------------------------------------------------------

NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=VotreSecretBase64TresLongEtSecurise==
WEB_PORT=3000
INTERNAL_API_KEY=abcdef1234567890abcdef1234567890abcdef1234567890

# ----------------------------------------------------------------------------
# SECTION 7: BACKUP
# ----------------------------------------------------------------------------

BACKUP_ENABLED=true
BACKUP_INTERVAL=6
BACKUP_RETENTION=10
BACKUP_PATH=./backups
BACKUP_COMPRESSION=true
BACKUP_INCLUDE_DATABASE=true
BACKUP_DISCORD_NOTIFY=true

# ----------------------------------------------------------------------------
# SECTION 8: MONITORING
# ----------------------------------------------------------------------------

MONITORING_ENABLED=true
MONITORING_INTERVAL=30
ALERT_TPS_WARNING=18
ALERT_TPS_CRITICAL=15
ALERT_RAM_WARNING=80
ALERT_RAM_CRITICAL=90
```

---

## Configuration avancee

### Variables d'environnement multiples

Vous pouvez creer des fichiers `.env` par environnement :
- `.env.development`
- `.env.staging`
- `.env.production`

### Surcharge avec docker-compose.override.yml

Creez un fichier `docker-compose.override.yml` pour surcharger la configuration par defaut :

```yaml
version: "3.9"

services:
  minecraft:
    environment:
      MEMORY: 8G
    ports:
      - "25566:25565"  # Port different
```

### Variables secretes avec Docker Secrets

Pour plus de securite en production :

```yaml
services:
  bot:
    secrets:
      - discord_token
      - db_password

secrets:
  discord_token:
    file: ./secrets/discord_token.txt
  db_password:
    file: ./secrets/db_password.txt
```

---

## Liens utiles

- [Installation](installation.md)
- [Services Docker](docker/services.md)
- [Troubleshooting](docker/troubleshooting.md)
