# Maintenance Docker

Guide de maintenance pour les services Docker du projet Minecraft.

---

## Table des matieres

- [Vue d'ensemble](#vue-densemble)
- [Mise a jour des services](#mise-a-jour-des-services)
- [Sauvegardes (Backups)](#sauvegardes-backups)
- [Restauration](#restauration)
- [Monitoring](#monitoring)
- [Nettoyage](#nettoyage)
- [Automatisation](#automatisation)
- [Troubleshooting maintenance](#troubleshooting-maintenance)

---

## Vue d'ensemble

La maintenance reguliere assure le bon fonctionnement et la securite du systeme.

### Calendrier recommande

| Tache | Frequence | Priorite |
|-------|-----------|----------|
| Backups automatiques | Toutes les 6h | Critique |
| Mise a jour images Docker | Hebdomadaire | Haute |
| Verification des logs | Quotidienne | Moyenne |
| Nettoyage Docker | Mensuel | Basse |
| Audit de securite | Trimestriel | Haute |

---

## Mise a jour des services

### Mise a jour des images Docker

```bash
# Telecharger les dernieres images
docker compose pull

# Recreer les conteneurs avec les nouvelles images
docker compose up -d

# Verifier que tout fonctionne
docker compose ps
```

### Mise a jour service par service

#### Minecraft

```bash
# Arreter proprement le serveur
docker compose exec minecraft rcon-cli stop

# Attendre l'arret complet
docker compose stop minecraft

# Mettre a jour
docker compose pull minecraft
docker compose up -d minecraft

# Verifier les logs
docker compose logs -f minecraft
```

> **Attention :** Faites toujours un backup avant de mettre a jour Minecraft !

#### Bot Discord

```bash
# Arreter le bot
docker compose stop bot

# Rebuild avec le nouveau code
docker compose build bot

# Redemarrer
docker compose up -d bot

# Verifier les logs
docker compose logs -f bot
```

#### Dashboard Web

```bash
# Arreter le service web
docker compose stop web

# Rebuild
docker compose build web

# Redemarrer
docker compose up -d web

# Verifier
docker compose logs -f web
```

#### PostgreSQL

> **Attention :** La mise a jour de PostgreSQL peut necessiter une migration de donnees !

```bash
# 1. Backup complet
docker compose exec db pg_dumpall -U minecraft_user > full_backup.sql

# 2. Arreter tous les services
docker compose down

# 3. Modifier la version dans docker-compose.yml
# image: postgres:17-alpine

# 4. Supprimer le volume (apres backup !)
docker volume rm minecraft_postgres-data

# 5. Redemarrer
docker compose up -d db

# 6. Restaurer
docker compose exec -T db psql -U minecraft_user < full_backup.sql
```

#### Redis

```bash
# Arreter Redis
docker compose stop redis

# Mettre a jour
docker compose pull redis
docker compose up -d redis

# Verifier
docker compose logs -f redis
```

### Mise a jour automatique (Watchtower)

Ajoutez Watchtower pour les mises a jour automatiques :

```yaml
# docker-compose.override.yml
services:
  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_SCHEDULE=0 0 4 * * *  # 4h du matin
      - WATCHTOWER_NOTIFICATIONS=slack
    restart: unless-stopped
```

---

## Sauvegardes (Backups)

### Types de backups

| Type | Contenu | Taille approx. |
|------|---------|----------------|
| Full | Tout (monde + DB + configs) | 2-5 GB |
| Worlds | Mondes Minecraft uniquement | 1-3 GB |
| Database | PostgreSQL uniquement | 50-500 MB |
| Quick | Monde principal | 500 MB - 2 GB |

### Backup manuel complet

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups/${DATE}"

mkdir -p ${BACKUP_DIR}

echo "=== Backup complet - ${DATE} ==="

# 1. Sauvegarder le monde Minecraft
echo "Sauvegarde du monde Minecraft..."
docker compose exec minecraft rcon-cli save-all
sleep 5
docker compose exec minecraft rcon-cli save-off

tar -czf ${BACKUP_DIR}/minecraft-world.tar.gz ./minecraft/world

docker compose exec minecraft rcon-cli save-on
echo "Monde sauvegarde."

# 2. Sauvegarder la base de donnees
echo "Sauvegarde de PostgreSQL..."
docker compose exec -T db pg_dump -U minecraft_user minecraft_db > ${BACKUP_DIR}/database.sql
gzip ${BACKUP_DIR}/database.sql
echo "Base de donnees sauvegardee."

# 3. Sauvegarder les configurations
echo "Sauvegarde des configurations..."
tar -czf ${BACKUP_DIR}/configs.tar.gz ./minecraft/config .env
echo "Configurations sauvegardees."

# 4. Sauvegarder Redis (optionnel)
echo "Sauvegarde de Redis..."
docker compose exec redis redis-cli -a ${REDIS_PASSWORD} BGSAVE
sleep 2
docker cp $(docker compose ps -q redis):/data/dump.rdb ${BACKUP_DIR}/redis.rdb
echo "Redis sauvegarde."

# Creer un fichier manifest
echo "Date: ${DATE}" > ${BACKUP_DIR}/manifest.txt
echo "Type: Full backup" >> ${BACKUP_DIR}/manifest.txt
ls -la ${BACKUP_DIR} >> ${BACKUP_DIR}/manifest.txt

echo "=== Backup termine : ${BACKUP_DIR} ==="
```

### Backup de la base de donnees

```bash
# Backup simple
docker compose exec -T db pg_dump -U minecraft_user minecraft_db > backup.sql

# Backup compresse
docker compose exec -T db pg_dump -U minecraft_user minecraft_db | gzip > backup.sql.gz

# Backup avec timestamp
docker compose exec -T db pg_dump -U minecraft_user minecraft_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup de toutes les bases
docker compose exec -T db pg_dumpall -U minecraft_user > full_backup.sql
```

### Backup du monde Minecraft

```bash
# Desactiver la sauvegarde automatique
docker compose exec minecraft rcon-cli save-off

# Forcer une sauvegarde
docker compose exec minecraft rcon-cli save-all

# Attendre la fin
sleep 5

# Copier le monde
tar -czf minecraft-world-$(date +%Y%m%d).tar.gz ./minecraft/world

# Reactiver la sauvegarde automatique
docker compose exec minecraft rcon-cli save-on
```

### Backup vers stockage distant

#### AWS S3

```bash
# Installer AWS CLI
pip install awscli

# Configurer
aws configure

# Upload
aws s3 cp ./backups/latest.tar.gz s3://my-bucket/minecraft-backups/
```

#### Google Cloud Storage

```bash
# Installer gsutil
pip install gsutil

# Upload
gsutil cp ./backups/latest.tar.gz gs://my-bucket/minecraft-backups/
```

#### Script de rotation

```bash
#!/bin/bash
# rotate-backups.sh

BACKUP_DIR="./backups"
RETENTION=10  # Garder les 10 derniers backups

# Lister et supprimer les anciens
ls -t ${BACKUP_DIR} | tail -n +$((RETENTION + 1)) | while read dir; do
    echo "Suppression de ${BACKUP_DIR}/${dir}"
    rm -rf "${BACKUP_DIR}/${dir}"
done

echo "Rotation terminee. ${RETENTION} backups conserves."
```

---

## Restauration

### Restauration complete

```bash
#!/bin/bash
# restore.sh BACKUP_DIR

BACKUP_DIR=$1

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: ./restore.sh <backup_directory>"
    exit 1
fi

echo "=== Restauration depuis ${BACKUP_DIR} ==="

# 1. Arreter tous les services
echo "Arret des services..."
docker compose down

# 2. Restaurer le monde Minecraft
echo "Restauration du monde..."
rm -rf ./minecraft/world
tar -xzf ${BACKUP_DIR}/minecraft-world.tar.gz

# 3. Restaurer la base de donnees
echo "Restauration de la base de donnees..."
docker compose up -d db
sleep 10  # Attendre que PostgreSQL demarre

gunzip -c ${BACKUP_DIR}/database.sql.gz | docker compose exec -T db psql -U minecraft_user minecraft_db

# 4. Restaurer les configurations
echo "Restauration des configurations..."
tar -xzf ${BACKUP_DIR}/configs.tar.gz

# 5. Redemarrer tous les services
echo "Redemarrage des services..."
docker compose up -d

echo "=== Restauration terminee ==="
```

### Restauration de la base de donnees

```bash
# Restauration simple
docker compose exec -T db psql -U minecraft_user minecraft_db < backup.sql

# Restauration depuis fichier compresse
gunzip -c backup.sql.gz | docker compose exec -T db psql -U minecraft_user minecraft_db

# Restauration avec recreation de la base
docker compose exec db psql -U minecraft_user -c "DROP DATABASE minecraft_db;"
docker compose exec db psql -U minecraft_user -c "CREATE DATABASE minecraft_db;"
docker compose exec -T db psql -U minecraft_user minecraft_db < backup.sql
```

### Restauration du monde Minecraft

```bash
# Arreter le serveur
docker compose stop minecraft

# Supprimer l'ancien monde
rm -rf ./minecraft/world

# Extraire le backup
tar -xzf minecraft-world-20240115.tar.gz

# Redemarrer
docker compose up -d minecraft
```

### Restauration partielle (table specifique)

```bash
# Extraire une table du backup
grep -A 9999 "COPY players" backup.sql | grep -B 9999 "\\." > players_only.sql

# Restaurer uniquement cette table
docker compose exec -T db psql -U minecraft_user minecraft_db < players_only.sql
```

---

## Monitoring

### Surveillance basique

```bash
# Statut de tous les conteneurs
docker compose ps

# Utilisation des ressources
docker stats

# Logs en temps reel
docker compose logs -f
```

### Script de monitoring

```bash
#!/bin/bash
# monitor.sh

echo "=== Monitoring $(date) ==="

# Statut des conteneurs
echo -e "\n--- Conteneurs ---"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# Utilisation memoire
echo -e "\n--- Memoire ---"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Utilisation disque
echo -e "\n--- Disque ---"
docker system df

# TPS Minecraft (si en ligne)
echo -e "\n--- TPS Minecraft ---"
docker compose exec -T minecraft rcon-cli "forge tps" 2>/dev/null || echo "Serveur hors ligne"

# Connexions PostgreSQL
echo -e "\n--- Connexions PostgreSQL ---"
docker compose exec -T db psql -U minecraft_user -c "SELECT count(*) as connections FROM pg_stat_activity;" 2>/dev/null

echo -e "\n=== Fin du monitoring ==="
```

### Alertes

Ajoutez des alertes avec un webhook Discord :

```bash
#!/bin/bash
# alert.sh

WEBHOOK_URL="https://discord.com/api/webhooks/xxx/yyy"

send_alert() {
    local message=$1
    curl -H "Content-Type: application/json" \
         -d "{\"content\": \"⚠️ **Alerte Serveur**\n${message}\"}" \
         ${WEBHOOK_URL}
}

# Verifier si un conteneur est down
for service in minecraft bot web db redis; do
    status=$(docker compose ps -q ${service} | xargs docker inspect -f '{{.State.Running}}' 2>/dev/null)
    if [ "$status" != "true" ]; then
        send_alert "Le service **${service}** est hors ligne !"
    fi
done
```

### Healthchecks externes

Utilisez des services comme [Uptime Robot](https://uptimerobot.com/) ou [Healthchecks.io](https://healthchecks.io/) :

```bash
# Ping healthchecks.io apres un backup reussi
curl -fsS --retry 3 https://hc-ping.com/your-uuid-here
```

---

## Nettoyage

### Nettoyage Docker

```bash
# Supprimer les conteneurs arretes
docker container prune -f

# Supprimer les images non utilisees
docker image prune -f

# Supprimer les volumes non utilises (ATTENTION !)
docker volume prune -f

# Supprimer les reseaux non utilises
docker network prune -f

# Nettoyage complet (ATTENTION !)
docker system prune -af --volumes
```

### Nettoyage des logs

```bash
# Voir la taille des logs Docker
du -sh /var/lib/docker/containers/*/*-json.log

# Limiter la taille des logs (docker-compose.yml)
services:
  minecraft:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Nettoyage des backups anciens

```bash
# Supprimer les backups de plus de 30 jours
find ./backups -type d -mtime +30 -exec rm -rf {} \;

# Script de rotation (garder les 10 derniers)
ls -t ./backups | tail -n +11 | xargs -I {} rm -rf ./backups/{}
```

### Script de nettoyage complet

```bash
#!/bin/bash
# cleanup.sh

echo "=== Nettoyage Docker ==="

# Conteneurs
echo "Nettoyage des conteneurs..."
docker container prune -f

# Images
echo "Nettoyage des images..."
docker image prune -f

# Build cache
echo "Nettoyage du cache de build..."
docker builder prune -f

# Espace recupere
echo -e "\n--- Espace disque ---"
docker system df

echo "=== Nettoyage termine ==="
```

---

## Automatisation

### Cron jobs (Linux)

```bash
# Editer crontab
crontab -e

# Ajouter les taches
# Backup toutes les 6 heures
0 */6 * * * /home/user/minecraft/scripts/backup.sh >> /var/log/minecraft-backup.log 2>&1

# Nettoyage Docker chaque dimanche a 3h
0 3 * * 0 docker system prune -f >> /var/log/docker-cleanup.log 2>&1

# Monitoring toutes les 5 minutes
*/5 * * * * /home/user/minecraft/scripts/monitor.sh >> /var/log/minecraft-monitor.log 2>&1

# Rotation des backups chaque jour a 4h
0 4 * * * /home/user/minecraft/scripts/rotate-backups.sh >> /var/log/backup-rotation.log 2>&1
```

### Taches planifiees (Windows)

```powershell
# Creer une tache planifiee pour le backup
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File C:\Minecraft\scripts\backup.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 4am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "Minecraft Backup" -Description "Backup quotidien du serveur Minecraft"
```

### Docker Compose avec restart policies

```yaml
services:
  minecraft:
    restart: unless-stopped
    # Redemarre automatiquement sauf si arrete manuellement

  bot:
    restart: always
    # Redemarre toujours

  db:
    restart: on-failure
    # Redemarre uniquement en cas d'echec
```

---

## Troubleshooting maintenance

### Backup echoue

**Symptome :** Le backup ne se termine pas ou produit des fichiers vides.

**Solutions :**

```bash
# Verifier l'espace disque
df -h

# Verifier les permissions
ls -la ./backups

# Tester manuellement
docker compose exec db pg_dump -U minecraft_user minecraft_db > test.sql
echo $?  # Doit retourner 0
```

### Restauration echouee

**Symptome :** Erreurs lors de la restauration de la base.

**Solutions :**

```bash
# Verifier le format du fichier
file backup.sql

# Verifier les erreurs de syntaxe
head -100 backup.sql

# Restaurer avec verbose
docker compose exec -T db psql -U minecraft_user minecraft_db -v ON_ERROR_STOP=1 < backup.sql
```

### Conteneur qui redémarre en boucle

**Symptome :** Un service redémarre continuellement.

**Solutions :**

```bash
# Voir les logs
docker compose logs --tail=100 service_name

# Verifier l'exit code
docker inspect $(docker compose ps -q service_name) | grep ExitCode

# Demarrer en mode interactif pour debug
docker compose run --rm service_name bash
```

### Espace disque insuffisant

**Symptome :** Erreurs "no space left on device".

**Solutions :**

```bash
# Verifier l'espace
df -h

# Identifier les plus gros fichiers
du -sh /var/lib/docker/*

# Nettoyage agressif
docker system prune -af --volumes

# Deplacer les volumes Docker
# Editer /etc/docker/daemon.json
{
  "data-root": "/mnt/docker-data"
}
```

---

## Liens connexes

- [Services Docker](services.md)
- [Configuration](../configuration.md)
- [Troubleshooting](../troubleshooting.md)
- [Logs](../logs.md)
