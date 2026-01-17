# Minecraft Server Manager - Guide de démarrage rapide

> **Temps estimé : 5 minutes**

Ce guide vous permet de mettre en place rapidement votre serveur Minecraft avec bot Discord et panel web.

---

## Table des matières

- [Prérequis](#prérequis)
- [Installation express](#installation-express)
- [Premier lancement](#premier-lancement)
- [Vérification](#vérification)
- [Prochaines étapes](#prochaines-étapes)

---

## Prérequis

Avant de commencer, assurez-vous d'avoir :

| Composant | Version minimum | Vérification |
|-----------|-----------------|--------------|
| Docker | 20.10+ | `docker --version` |
| Docker Compose | 2.0+ | `docker compose version` |
| Git | 2.30+ | `git --version` |
| RAM disponible | 8 Go minimum | - |
| Espace disque | 20 Go minimum | - |

### Prérequis Discord

1. Un compte Discord
2. Une application Discord créée sur le [Developer Portal](https://discord.com/developers/applications)
3. Un bot créé avec le token récupéré
4. Les identifiants OAuth2 (Client ID et Client Secret)

---

## Installation express

### Étape 1 : Cloner le projet

```bash
git clone <url-du-repo> minecraft-server
cd minecraft-server
```

### Étape 2 : Lancer le script de configuration

**Windows (PowerShell) :**
```powershell
.\setup.ps1
```

**Linux/macOS :**
```bash
chmod +x setup.sh
./setup.sh
```

### Étape 3 : Répondre aux questions

Le script vous demandera :
- **Nom du projet** : ex. `MonServeur`
- **Token Discord** : récupéré sur le Developer Portal
- **Guild ID** : ID de votre serveur Discord
- **Client ID** : ID de l'application Discord
- **Client Secret** : Secret OAuth2

> **Note** : Les mots de passe pour PostgreSQL, Redis et RCON sont générés automatiquement.

---

## Premier lancement

### Démarrer tous les services

```bash
docker compose up -d
```

### Vérifier le statut

```bash
docker compose ps
```

Vous devriez voir tous les services en état `running` :

```
NAME                    STATUS
monserveur-minecraft    running
monserveur-bot          running
monserveur-web          running
monserveur-db           running
monserveur-redis        running
```

### Consulter les logs

```bash
# Tous les services
docker compose logs -f

# Un service spécifique
docker compose logs -f bot
docker compose logs -f minecraft
```

---

## Vérification

### 1. Serveur Minecraft

Connectez-vous avec votre client Minecraft :
- **Adresse** : `localhost` ou `votre-ip`
- **Port** : `25565`

### 2. Bot Discord

Le bot devrait apparaître en ligne sur votre serveur Discord. Testez avec :
```
/server status
```

### 3. Panel Web

Ouvrez votre navigateur :
- **URL** : `http://localhost:3000`

Connectez-vous avec votre compte Discord.

---

## Prochaines étapes

| Étape | Documentation |
|-------|---------------|
| Configuration avancée | [configuration.md](configuration.md) |
| Commandes du bot | [bot/commands.md](bot/commands.md) |
| Gestion des permissions | [bot/permissions.md](bot/permissions.md) |
| Configuration Docker | [docker/services.md](docker/services.md) |
| Personnalisation | [customization.md](customization.md) |

---

## Commandes rapides

```bash
# Démarrer les services
docker compose up -d

# Arrêter les services
docker compose down

# Redémarrer un service
docker compose restart bot

# Voir les logs en temps réel
docker compose logs -f

# Mettre à jour les images
docker compose pull
docker compose up -d

# Sauvegarder la base de données
docker compose exec db pg_dump -U postgres > backup.sql
```

---

## Support

- **Documentation complète** : Consultez les autres fichiers dans `/docs`
- **Issues** : Ouvrez une issue sur le repository GitHub
- **Discord** : Rejoignez le serveur de support

---

> **Astuce** : Pour une configuration plus détaillée, consultez [installation.md](installation.md).
