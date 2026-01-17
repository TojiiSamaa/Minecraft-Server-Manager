# Guide d'installation détaillé

Ce guide couvre l'installation complète du projet sur Windows, Linux et macOS.

---

## Table des matières

- [Prérequis détaillés](#prérequis-détaillés)
- [Installation Windows (PowerShell)](#installation-windows-powershell)
- [Installation Linux (Bash)](#installation-linux-bash)
- [Installation macOS](#installation-macos)
- [Installation manuelle](#installation-manuelle)
- [Configuration post-installation](#configuration-post-installation)
- [Dépannage installation](#dépannage-installation)

---

## Prérequis détaillés

### Docker Desktop

#### Windows
1. Télécharger [Docker Desktop pour Windows](https://www.docker.com/products/docker-desktop)
2. Installer et redémarrer
3. Activer WSL 2 si demandé
4. Vérifier : `docker --version`

#### Linux (Ubuntu/Debian)
```bash
# Mise à jour des paquets
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Ajout du repository Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Installation
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER
newgrp docker

# Vérification
docker --version
docker compose version
```

#### macOS
1. Télécharger [Docker Desktop pour Mac](https://www.docker.com/products/docker-desktop)
2. Installer le fichier .dmg
3. Lancer Docker Desktop
4. Vérifier : `docker --version`

### Configuration Discord

1. Rendez-vous sur le [Discord Developer Portal](https://discord.com/developers/applications)
2. Cliquez sur **New Application**
3. Donnez un nom à votre application

#### Créer le bot
1. Allez dans **Bot** dans le menu latéral
2. Cliquez sur **Add Bot**
3. Copiez le **Token** (gardez-le secret !)
4. Activez les options :
   - **Presence Intent**
   - **Server Members Intent**
   - **Message Content Intent**

#### Récupérer les identifiants OAuth2
1. Allez dans **OAuth2** > **General**
2. Copiez le **Client ID**
3. Copiez le **Client Secret**
4. Ajoutez l'URL de redirection : `http://localhost:3000/api/auth/callback/discord`

#### Inviter le bot
1. Allez dans **OAuth2** > **URL Generator**
2. Sélectionnez les scopes : `bot`, `applications.commands`
3. Sélectionnez les permissions :
   - Send Messages
   - Embed Links
   - Read Message History
   - Use Slash Commands
   - Manage Messages (optionnel)
4. Copiez l'URL générée et ouvrez-la pour inviter le bot

#### Récupérer le Guild ID
1. Dans Discord, activez le mode développeur (Paramètres > Avancé)
2. Clic droit sur votre serveur > Copier l'identifiant

---

## Installation Windows (PowerShell)

### Étape 1 : Préparer l'environnement

```powershell
# Ouvrir PowerShell en tant qu'administrateur
# Vérifier la version de PowerShell
$PSVersionTable.PSVersion

# Doit être >= 5.1
```

### Étape 2 : Cloner et configurer

```powershell
# Cloner le repository
git clone <url-du-repo> C:\Minecraft
cd C:\Minecraft

# Autoriser l'exécution des scripts (si nécessaire)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Lancer le script d'installation
.\setup.ps1
```

### Étape 3 : Suivre l'assistant

Le script vous guidera à travers :
1. Vérification des prérequis (Docker, PowerShell)
2. Saisie des informations Discord
3. Génération automatique des secrets
4. Création des fichiers de configuration
5. Création de la structure de dossiers

### Étape 4 : Démarrer les services

```powershell
# Démarrer tous les services
docker compose up -d

# Vérifier le statut
docker compose ps

# Consulter les logs
docker compose logs -f
```

---

## Installation Linux (Bash)

### Étape 1 : Préparer l'environnement

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer les dépendances
sudo apt install -y git curl openssl

# Vérifier Docker
docker --version
docker compose version
```

### Étape 2 : Cloner et configurer

```bash
# Cloner le repository
git clone <url-du-repo> ~/minecraft-server
cd ~/minecraft-server

# Rendre le script exécutable
chmod +x setup.sh

# Lancer le script d'installation
./setup.sh
```

### Étape 3 : Configuration interactive

Le script vous demandera :
- Nom du projet
- Token Discord
- Guild ID
- Client ID
- Client Secret

### Étape 4 : Démarrer les services

```bash
# Démarrer tous les services
docker compose up -d

# Vérifier le statut
docker compose ps

# Consulter les logs
docker compose logs -f
```

### Étape 5 : Configuration systemd (optionnel)

Pour démarrer automatiquement au boot :

```bash
# Créer le fichier service
sudo nano /etc/systemd/system/minecraft-bot.service
```

Contenu :
```ini
[Unit]
Description=Minecraft Server Manager
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/user/minecraft-server
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=user

[Install]
WantedBy=multi-user.target
```

```bash
# Activer le service
sudo systemctl enable minecraft-bot
sudo systemctl start minecraft-bot
```

---

## Installation macOS

### Étape 1 : Installer Homebrew (si nécessaire)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Étape 2 : Installer les dépendances

```bash
brew install git openssl
```

### Étape 3 : Installation

```bash
# Cloner le repository
git clone <url-du-repo> ~/minecraft-server
cd ~/minecraft-server

# Rendre le script exécutable
chmod +x setup.sh

# Lancer le script
./setup.sh
```

### Étape 4 : Démarrer

```bash
docker compose up -d
```

---

## Installation manuelle

Si vous préférez configurer manuellement :

### 1. Créer le fichier .env

```bash
cp templates/env.template .env
```

### 2. Éditer le fichier .env

Remplacez les placeholders par vos valeurs :

```env
# Discord
DISCORD_TOKEN=votre_token_ici
DISCORD_GUILD_ID=votre_guild_id
DISCORD_CLIENT_ID=votre_client_id
DISCORD_CLIENT_SECRET=votre_client_secret

# Générer les mots de passe (Linux/macOS)
RCON_PASSWORD=$(openssl rand -base64 24)
POSTGRES_PASSWORD=$(openssl rand -base64 24)
REDIS_PASSWORD=$(openssl rand -base64 24)
NEXTAUTH_SECRET=$(openssl rand -base64 32)
```

### 3. Créer le docker-compose.yml

```bash
cp templates/docker-compose.template.yml docker-compose.yml
# Remplacer les placeholders
sed -i 's/{{PROJECT_NAME_LOWER}}/monserveur/g' docker-compose.yml
```

### 4. Démarrer les services

```bash
docker compose up -d
```

---

## Configuration post-installation

### Vérifier la connexion du bot

```bash
# Voir les logs du bot
docker compose logs bot

# Vous devriez voir :
# [INFO] Bot connecté en tant que VotreBot#1234
# [INFO] Synchronisation des commandes slash...
# [INFO] Prêt !
```

### Configurer les channels Discord

1. Utilisez la commande `/notifications configure` dans Discord
2. Sélectionnez les channels pour chaque type de notification

### Sauvegarder les secrets

> **IMPORTANT** : Sauvegardez votre fichier `.env` dans un endroit sûr !

Les secrets générés sont :
- `RCON_PASSWORD` - Mot de passe RCON Minecraft
- `POSTGRES_PASSWORD` - Mot de passe PostgreSQL
- `REDIS_PASSWORD` - Mot de passe Redis
- `NEXTAUTH_SECRET` - Secret pour les sessions web
- `INTERNAL_API_KEY` - Clé API interne

---

## Dépannage installation

### Docker ne démarre pas

**Windows :**
```powershell
# Vérifier le service Docker
Get-Service docker

# Redémarrer Docker Desktop
Stop-Process -Name "Docker Desktop" -Force
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

**Linux :**
```bash
# Vérifier le service
sudo systemctl status docker

# Redémarrer Docker
sudo systemctl restart docker
```

### Erreur de permission (Linux)

```bash
# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER

# Déconnecter et reconnecter ou utiliser
newgrp docker
```

### Port déjà utilisé

```bash
# Trouver le processus utilisant le port
# Windows
netstat -ano | findstr :25565

# Linux/macOS
sudo lsof -i :25565

# Tuer le processus ou changer le port dans .env
```

### Le bot ne se connecte pas

1. Vérifier le token Discord
2. Vérifier que les Intents sont activés dans le Developer Portal
3. Vérifier les logs : `docker compose logs bot`

### Erreur de connexion à la base de données

```bash
# Vérifier que PostgreSQL est démarré
docker compose ps db

# Vérifier les logs
docker compose logs db

# Redémarrer le service
docker compose restart db
```

### Minecraft ne démarre pas

```bash
# Vérifier les logs
docker compose logs minecraft

# Causes courantes :
# - EULA non acceptée -> vérifier EULA=TRUE dans .env
# - Mémoire insuffisante -> augmenter MINECRAFT_MEMORY
# - Port déjà utilisé -> changer MINECRAFT_PORT
```

### Réinitialiser l'installation

```bash
# Arrêter tous les services
docker compose down -v

# Supprimer les volumes (ATTENTION : perte de données !)
docker volume prune -f

# Relancer l'installation
./setup.sh  # ou .\setup.ps1
```

---

## Prochaines étapes

- [Configuration avancée](configuration.md)
- [Commandes du bot](bot/commands.md)
- [Services Docker](docker/services.md)

---

> **Besoin d'aide ?** Consultez la section [Dépannage Docker](docker/troubleshooting.md) pour plus de solutions.
