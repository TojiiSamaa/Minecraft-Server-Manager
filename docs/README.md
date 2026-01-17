# Minecraft Server Manager - Guide de demarrage rapide

> **Temps estime : 5 minutes**

Ce guide vous permet de mettre en place rapidement votre serveur Minecraft avec bot Discord et panel web.

---

## Table des matieres

- [Prerequis](#prerequis)
- [Installation express](#installation-express)
- [Premier lancement](#premier-lancement)
- [Verification](#verification)
- [Prochaines etapes](#prochaines-etapes)

---

## Prerequis

Avant de commencer, assurez-vous d'avoir :

| Composant | Version minimum | Verification |
|-----------|-----------------|--------------|
| Docker | 20.10+ | `docker --version` |
| Docker Compose | 2.0+ | `docker compose version` |
| Git | 2.30+ | `git --version` |
| RAM disponible | 8 Go minimum | - |
| Espace disque | 20 Go minimum | - |

### Prerequis Discord

1. Un compte Discord
2. Une application Discord creee sur le [Developer Portal](https://discord.com/developers/applications)
3. Un bot cree avec le token recupere
4. Les identifiants OAuth2 (Client ID et Client Secret)

---

## Installation express

### Etape 1 : Cloner le projet

```bash
git clone <url-du-repo> minecraft-server
cd minecraft-server
```

### Etape 2 : Lancer le script de configuration

**Windows (PowerShell) :**
```powershell
.\setup.ps1
```

**Linux/macOS :**
```bash
chmod +x setup.sh
./setup.sh
```

### Etape 3 : Repondre aux questions

Le script vous demandera :
- **Nom du projet** : ex. `MonServeur`
- **Token Discord** : recupere sur le Developer Portal
- **Guild ID** : ID de votre serveur Discord
- **Client ID** : ID de l'application Discord
- **Client Secret** : Secret OAuth2

> **Note** : Les mots de passe pour PostgreSQL, Redis et RCON sont generes automatiquement.

---

## Premier lancement

### Demarrer tous les services

```bash
docker compose up -d
```

### Verifier le statut

```bash
docker compose ps
```

Vous devriez voir tous les services en etat `running` :

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

# Un service specifique
docker compose logs -f bot
docker compose logs -f minecraft
```

---

## Verification

### 1. Serveur Minecraft

Connectez-vous avec votre client Minecraft :
- **Adresse** : `localhost` ou `votre-ip`
- **Port** : `25565`

### 2. Bot Discord

Le bot devrait apparaitre en ligne sur votre serveur Discord. Testez avec :
```
/server status
```

### 3. Panel Web

Ouvrez votre navigateur :
- **URL** : `http://localhost:3000`

Connectez-vous avec votre compte Discord.

---

## Prochaines etapes

| Etape | Documentation |
|-------|---------------|
| Configuration avancee | [configuration.md](configuration.md) |
| Commandes du bot | [bot/commands.md](bot/commands.md) |
| Gestion des permissions | [bot/permissions.md](bot/permissions.md) |
| Configuration Docker | [docker/services.md](docker/services.md) |
| Personnalisation | [customization.md](customization.md) |

---

## Commandes rapides

```bash
# Demarrer les services
docker compose up -d

# Arreter les services
docker compose down

# Redemarrer un service
docker compose restart bot

# Voir les logs en temps reel
docker compose logs -f

# Mettre a jour les images
docker compose pull
docker compose up -d

# Sauvegarder la base de donnees
docker compose exec db pg_dump -U postgres > backup.sql
```

---

## Support

- **Documentation complete** : Consultez les autres fichiers dans `/docs`
- **Issues** : Ouvrez une issue sur le repository GitHub
- **Discord** : Rejoignez le serveur de support

---

> **Astuce** : Pour une configuration plus detaillee, consultez [installation.md](installation.md).
