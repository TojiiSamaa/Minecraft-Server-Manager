# Guide de Dépannage

Solutions aux problèmes courants du projet Minecraft Server Manager.

---

## Table des matières

- [Erreurs courantes](#erreurs-courantes)
- [Docker ne démarre pas](#docker-ne-démarre-pas)
- [Bot ne se connecte pas](#bot-ne-se-connecte-pas)
- [RCON timeout](#rcon-timeout)
- [Problèmes de base de données](#problèmes-de-base-de-données)
- [Problèmes du dashboard web](#problèmes-du-dashboard-web)
- [Problèmes Minecraft](#problèmes-minecraft)
- [Problèmes de performance](#problèmes-de-performance)
- [Outils de diagnostic](#outils-de-diagnostic)

---

## Erreurs courantes

### Tableau de référence rapide

| Erreur | Cause probable | Solution |
|--------|----------------|----------|
| `RCON timeout` | Serveur Minecraft hors ligne | Vérifier le conteneur minecraft |
| `Permission denied` | Rôle Discord mal configuré | Vérifier DISCORD_ADMIN_ROLE_ID |
| `Database connection refused` | PostgreSQL non démarré | `docker compose up -d db` |
| `Invalid token` | Token Discord incorrect | Vérifier DISCORD_TOKEN |
| `Port already in use` | Port occupé | Changer le port ou tuer le processus |
| `Out of memory` | RAM insuffisante | Augmenter MINECRAFT_MEMORY_MAX |

---

## Docker ne démarre pas

### Symptôme : Les conteneurs ne démarrent pas

**Diagnostic :**

```bash
# Vérifier le statut de Docker
docker info

# Vérifier les conteneurs
docker compose ps -a

# Voir les logs de démarrage
docker compose logs
```

### Erreur : "Cannot connect to Docker daemon"

**Cause :** Le service Docker n'est pas démarré.

**Solution Windows :**

```powershell
# Vérifier le service
Get-Service docker

# Démarrer Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Attendre le démarrage (30-60 secondes)
```

**Solution Linux :**

```bash
# Vérifier le service
sudo systemctl status docker

# Démarrer Docker
sudo systemctl start docker

# Activer au démarrage
sudo systemctl enable docker
```

### Erreur : "Bind for 0.0.0.0:25565 failed: port is already allocated"

**Cause :** Le port est déjà utilisé par un autre processus.

**Solution :**

```bash
# Windows - Trouver le processus
netstat -ano | findstr :25565
# Puis tuer le processus
taskkill /PID <PID> /F

# Linux - Trouver le processus
sudo lsof -i :25565
# Puis tuer le processus
sudo kill -9 <PID>

# OU changer le port dans .env
MINECRAFT_PORT=25566
```

### Erreur : "no space left on device"

**Cause :** Disque plein.

**Solution :**

```bash
# Vérifier l'espace disque
df -h

# Nettoyer Docker
docker system prune -af

# Nettoyer les volumes non utilisés
docker volume prune -f

# Nettoyer les images non utilisées
docker image prune -af
```

### Erreur : "network minecraft-network not found"

**Cause :** Le réseau Docker n'existe pas.

**Solution :**

```bash
# Créer le réseau
docker network create minecraft-network

# OU recréer tous les services
docker compose down
docker compose up -d
```

---

## Bot ne se connecte pas

### Symptôme : Le bot n'apparaît pas en ligne sur Discord

**Diagnostic :**

```bash
# Voir les logs du bot
docker compose logs bot

# Vérifier que le conteneur tourne
docker compose ps bot
```

### Erreur : "Invalid token"

**Cause :** Le token Discord est incorrect ou expiré.

**Solution :**

1. Allez sur le [Discord Developer Portal](https://discord.com/developers/applications)
2. Sélectionnez votre application
3. Allez dans **Bot**
4. Cliquez sur **Reset Token**
5. Copiez le nouveau token
6. Mettez à jour `.env` :

```env
DISCORD_TOKEN=nouveau_token_ici
```

7. Redémarrez le bot :

```bash
docker compose restart bot
```

### Erreur : "Privileged intents required"

**Cause :** Les intents privilégiés ne sont pas activés.

**Solution :**

1. Allez sur le Discord Developer Portal
2. Sélectionnez votre application > **Bot**
3. Activez :
   - **Presence Intent**
   - **Server Members Intent**
   - **Message Content Intent**
4. Sauvegardez et redémarrez le bot

### Erreur : "Missing Access"

**Cause :** Le bot n'a pas les permissions nécessaires.

**Solution :**

1. Réinvitez le bot avec les bonnes permissions :
   - Send Messages
   - Embed Links
   - Read Message History
   - Use Slash Commands
   - Manage Messages (optionnel)

2. URL de réinvitation :

```
https://discord.com/api/oauth2/authorize?client_id=VOTRE_CLIENT_ID&permissions=274878221376&scope=bot%20applications.commands
```

### Erreur : "Guild not found" ou commandes non visibles

**Cause :** Le Guild ID est incorrect ou les commandes ne sont pas synchronisées.

**Solution :**

1. Vérifiez le DISCORD_GUILD_ID dans `.env`
2. Synchronisez les commandes :

```
/admin sync
```

ou redémarrez le bot :

```bash
docker compose restart bot
```

---

## RCON timeout

### Symptôme : Erreur "RCON connection timeout" dans les logs

**Diagnostic :**

```bash
# Vérifier que le serveur Minecraft est démarré
docker compose ps minecraft

# Tester la connexion RCON manuellement
docker compose exec minecraft rcon-cli list
```

### Cause 1 : Serveur Minecraft non démarré

**Solution :**

```bash
# Démarrer le serveur
docker compose up -d minecraft

# Attendre le démarrage complet (vérifier les logs)
docker compose logs -f minecraft
# Attendre "Done (XXs)! For help, type "help""
```

### Cause 2 : Mauvais mot de passe RCON

**Solution :**

1. Vérifiez que le mot de passe dans `.env` correspond :

```env
RCON_PASSWORD=votre_mot_de_passe
```

2. Vérifiez dans les logs Minecraft :

```bash
docker compose logs minecraft | grep -i rcon
```

### Cause 3 : Mauvais host/port RCON

**Solution :**

Vérifiez `.env` :

```env
RCON_HOST=minecraft   # Nom du service Docker, pas localhost
RCON_PORT=25575
```

### Cause 4 : Serveur Minecraft en cours de démarrage

**Solution :**

Le serveur peut prendre 1-5 minutes pour démarrer complètement. Attendez le message "Done" dans les logs :

```bash
docker compose logs -f minecraft | grep -i "Done"
```

### Augmenter le timeout

Si le serveur est lent, augmentez le timeout :

```env
RCON_TIMEOUT=10.0   # 10 secondes au lieu de 5
```

---

## Problèmes de base de données

### Symptôme : "Connection refused" à PostgreSQL

**Diagnostic :**

```bash
# Vérifier le conteneur
docker compose ps db

# Voir les logs
docker compose logs db
```

### Erreur : "Connection refused"

**Cause :** PostgreSQL n'est pas démarré ou pas prêt.

**Solution :**

```bash
# Démarrer PostgreSQL
docker compose up -d db

# Attendre que le healthcheck passe
docker compose ps db
# STATUS doit être "healthy"
```

### Erreur : "Authentication failed"

**Cause :** Mauvais identifiants.

**Solution :**

1. Vérifiez `.env` :

```env
POSTGRES_USER=minecraft_user
POSTGRES_PASSWORD=votre_password
POSTGRES_DB=minecraft_db
DATABASE_URL=postgresql://minecraft_user:votre_password@db:5432/minecraft_db
```

2. Si le mot de passe a changé, recréez le conteneur :

```bash
docker compose down
docker volume rm minecraft_postgres-data
docker compose up -d db
```

> **Attention :** Cela supprime toutes les données !

### Erreur : "Database does not exist"

**Solution :**

```bash
# Créer la base de données
docker compose exec db psql -U minecraft_user -c "CREATE DATABASE minecraft_db;"
```

### Corruption de la base

**Solution :**

```bash
# Sauvegarder ce qui peut l'être
docker compose exec db pg_dump -U minecraft_user minecraft_db > emergency_backup.sql

# Restaurer depuis un backup
docker compose exec -T db psql -U minecraft_user minecraft_db < backup.sql
```

---

## Problèmes du dashboard web

### Symptôme : Page blanche ou erreur 500

**Diagnostic :**

```bash
# Voir les logs
docker compose logs web

# Vérifier le statut
docker compose ps web
```

### Erreur : "NEXTAUTH_SECRET is not set"

**Solution :**

Générez un secret et ajoutez-le à `.env` :

```bash
# Générer un secret
openssl rand -base64 32

# Ajouter à .env
NEXTAUTH_SECRET=votre_secret_genere_ici
```

### Erreur OAuth : "Redirect URI mismatch"

**Cause :** L'URL de callback n'est pas configurée dans Discord.

**Solution :**

1. Allez sur le Discord Developer Portal
2. OAuth2 > General
3. Ajoutez l'URL de redirect :

```
http://localhost:3000/api/auth/callback/discord
```

Pour la production :

```
https://votre-domaine.fr/api/auth/callback/discord
```

### Erreur : "Unable to fetch session"

**Cause :** NEXTAUTH_URL mal configuré.

**Solution :**

```env
NEXTAUTH_URL=http://localhost:3000  # ou votre URL de production
```

### Le dashboard ne charge pas les données

**Cause :** L'API interne n'est pas accessible.

**Solution :**

```bash
# Vérifier que le bot est accessible
docker compose exec web curl http://bot:8080/health

# Vérifier INTERNAL_API_KEY
# Doit être identique dans web et bot
```

---

## Problèmes Minecraft

### Symptôme : Le serveur crash au démarrage

**Diagnostic :**

```bash
# Voir les logs
docker compose logs minecraft

# Chercher les erreurs
docker compose logs minecraft | grep -i "error\|exception\|crash"
```

### Erreur : "EULA not accepted"

**Solution :**

Ajoutez à `.env` :

```env
EULA=TRUE
```

### Erreur : "Out of memory"

**Cause :** RAM insuffisante.

**Solution :**

1. Augmentez la mémoire dans `.env` :

```env
MINECRAFT_MEMORY_MIN=2G
MINECRAFT_MEMORY_MAX=4G
```

2. Vérifiez que votre machine a assez de RAM :

```bash
# Linux
free -h

# Windows
systeminfo | findstr "Memory"
```

### Erreur : "Failed to bind to port"

**Cause :** Le port est déjà utilisé.

**Solution :** Voir la section [Port already in use](#erreur--bind-for-00002556-failed-port-is-already-allocated).

### Les mods ne chargent pas

**Diagnostic :**

```bash
docker compose logs minecraft | grep -i "mod\|forge\|neoforge"
```

**Solutions :**

1. Vérifiez que les mods sont compatibles avec la version de Minecraft
2. Vérifiez que les mods sont dans le bon dossier : `./minecraft/mods/`
3. Vérifiez les permissions des fichiers

### Le monde est corrompu

**Solution :**

```bash
# Arrêter le serveur
docker compose stop minecraft

# Restaurer depuis un backup
rm -rf ./minecraft/world
tar -xzf ./backups/minecraft-world-YYYYMMDD.tar.gz

# Redémarrer
docker compose up -d minecraft
```

---

## Problèmes de performance

### Symptôme : TPS bas (< 20)

**Diagnostic :**

```bash
# Vérifier le TPS
docker compose exec minecraft rcon-cli "forge tps"
```

**Solutions :**

1. **Réduire la distance de rendu :**

```env
MINECRAFT_VIEW_DISTANCE=8
```

2. **Augmenter la RAM :**

```env
MINECRAFT_MEMORY_MAX=6G
```

3. **Limiter les entités :**

```bash
docker compose exec minecraft rcon-cli "kill @e[type=!player]"
```

### Symptôme : Bot lent à répondre

**Diagnostic :**

```bash
# Vérifier les ressources
docker stats
```

**Solutions :**

1. Vérifiez la connexion à Discord (latence)
2. Vérifiez les performances de la base de données :

```sql
SELECT * FROM pg_stat_activity;
```

### Symptôme : Dashboard lent

**Solutions :**

1. Activez le cache Redis
2. Optimisez les requêtes à la base de données
3. Utilisez la pagination pour les longues listes

---

## Outils de diagnostic

### Script de diagnostic complet

```bash
#!/bin/bash
# diagnostic.sh

echo "=== Diagnostic Minecraft Server Manager ==="
echo "Date: $(date)"
echo ""

echo "--- Docker ---"
docker --version
docker compose version
echo ""

echo "--- Conteneurs ---"
docker compose ps
echo ""

echo "--- Ressources ---"
docker stats --no-stream
echo ""

echo "--- Logs récents (erreurs) ---"
echo "Bot:"
docker compose logs --tail=20 bot 2>&1 | grep -i "error\|exception" || echo "Aucune erreur"
echo ""
echo "Minecraft:"
docker compose logs --tail=20 minecraft 2>&1 | grep -i "error\|exception" || echo "Aucune erreur"
echo ""

echo "--- Connexions ---"
echo "PostgreSQL:"
docker compose exec -T db psql -U minecraft_user -c "SELECT count(*) FROM pg_stat_activity;" 2>&1 || echo "Non disponible"
echo ""
echo "Redis:"
docker compose exec -T redis redis-cli -a ${REDIS_PASSWORD} ping 2>&1 || echo "Non disponible"
echo ""

echo "--- Espace disque ---"
df -h | grep -E "^/dev|Filesystem"
echo ""

echo "--- Volumes Docker ---"
docker volume ls
echo ""

echo "=== Fin du diagnostic ==="
```

### Commandes utiles

```bash
# Voir tous les logs en temps réel
docker compose logs -f

# Voir les logs d'un service spécifique
docker compose logs -f bot

# Redémarrer tous les services
docker compose restart

# Recréer les conteneurs
docker compose up -d --force-recreate

# Accéder à un conteneur
docker compose exec bot bash
docker compose exec minecraft rcon-cli

# Vérifier la santé des services
docker compose ps

# Voir l'utilisation des ressources
docker stats
```

### Collecte d'informations pour le support

```bash
# Créer un rapport de debug
{
    echo "=== Rapport de debug ==="
    echo "Date: $(date)"
    docker --version
    docker compose version
    docker compose ps
    docker compose logs --tail=100
} > debug_report.txt 2>&1

echo "Rapport généré : debug_report.txt"
```

---

## Obtenir de l'aide supplémentaire

Si vous n'avez pas trouvé de solution :

1. **Vérifiez la documentation** : Consultez les autres fichiers de documentation
2. **Cherchez dans les logs** : Les erreurs sont souvent explicites
3. **Redémarrez les services** : `docker compose restart`
4. **Recréez les conteneurs** : `docker compose up -d --force-recreate`
5. **Ouvrez une issue** : Sur le repository GitHub avec le rapport de debug

---

## Liens connexes

- [Installation](installation.md)
- [Configuration](configuration.md)
- [Services Docker](docker/services.md)
- [Maintenance](docker/maintenance.md)
- [Logs](logs.md)
