# Guide d'installation detaille

Ce guide couvre l'installation complete du projet sur Windows, Linux et macOS.

---

## Table des matieres

- [Prerequis detailles](#prerequis-detailles)
- [Installation Windows (PowerShell)](#installation-windows-powershell)
- [Installation Linux (Bash)](#installation-linux-bash)
- [Installation macOS](#installation-macos)
- [Installation manuelle](#installation-manuelle)
- [Configuration post-installation](#configuration-post-installation)
- [Troubleshooting installation](#troubleshooting-installation)

---

## Prerequis detailles

### Docker Desktop

#### Windows
1. Telecharger [Docker Desktop pour Windows](https://www.docker.com/products/docker-desktop)
2. Installer et redemarrer
3. Activer WSL 2 si demande
4. Verifier : `docker --version`

#### Linux (Ubuntu/Debian)
```bash
# Mise a jour des paquets
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

# Verification
docker --version
docker compose version
```

#### macOS
1. Telecharger [Docker Desktop pour Mac](https://www.docker.com/products/docker-desktop)
2. Installer le fichier .dmg
3. Lancer Docker Desktop
4. Verifier : `docker --version`

### Configuration Discord

1. Rendez-vous sur le [Discord Developer Portal](https://discord.com/developers/applications)
2. Cliquez sur **New Application**
3. Donnez un nom a votre application

#### Creer le bot
1. Allez dans **Bot** dans le menu lateral
2. Cliquez sur **Add Bot**
3. Copiez le **Token** (gardez-le secret !)
4. Activez les options :
   - **Presence Intent**
   - **Server Members Intent**
   - **Message Content Intent**

#### Recuperer les identifiants OAuth2
1. Allez dans **OAuth2** > **General**
2. Copiez le **Client ID**
3. Copiez le **Client Secret**
4. Ajoutez l'URL de redirection : `http://localhost:3000/api/auth/callback/discord`

#### Inviter le bot
1. Allez dans **OAuth2** > **URL Generator**
2. Selectionnez les scopes : `bot`, `applications.commands`
3. Selectionnez les permissions :
   - Send Messages
   - Embed Links
   - Read Message History
   - Use Slash Commands
   - Manage Messages (optionnel)
4. Copiez l'URL generee et ouvrez-la pour inviter le bot

#### Recuperer le Guild ID
1. Dans Discord, activez le mode developpeur (Parametres > Avance)
2. Clic droit sur votre serveur > Copier l'identifiant

---

## Installation Windows (PowerShell)

### Etape 1 : Preparer l'environnement

```powershell
# Ouvrir PowerShell en tant qu'administrateur
# Verifier la version de PowerShell
$PSVersionTable.PSVersion

# Doit etre >= 5.1
```

### Etape 2 : Cloner et configurer

```powershell
# Cloner le repository
git clone <url-du-repo> C:\Minecraft
cd C:\Minecraft

# Autoriser l'execution des scripts (si necessaire)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Lancer le script d'installation
.\setup.ps1
```

### Etape 3 : Suivre l'assistant

Le script vous guidera a travers :
1. Verification des prerequis (Docker, PowerShell)
2. Saisie des informations Discord
3. Generation automatique des secrets
4. Creation des fichiers de configuration
5. Creation de la structure de dossiers

### Etape 4 : Demarrer les services

```powershell
# Demarrer tous les services
docker compose up -d

# Verifier le statut
docker compose ps

# Consulter les logs
docker compose logs -f
```

---

## Installation Linux (Bash)

### Etape 1 : Preparer l'environnement

```bash
# Mettre a jour le systeme
sudo apt update && sudo apt upgrade -y

# Installer les dependances
sudo apt install -y git curl openssl

# Verifier Docker
docker --version
docker compose version
```

### Etape 2 : Cloner et configurer

```bash
# Cloner le repository
git clone <url-du-repo> ~/minecraft-server
cd ~/minecraft-server

# Rendre le script executable
chmod +x setup.sh

# Lancer le script d'installation
./setup.sh
```

### Etape 3 : Configuration interactive

Le script vous demandera :
- Nom du projet
- Token Discord
- Guild ID
- Client ID
- Client Secret

### Etape 4 : Demarrer les services

```bash
# Demarrer tous les services
docker compose up -d

# Verifier le statut
docker compose ps

# Consulter les logs
docker compose logs -f
```

### Etape 5 : Configuration systemd (optionnel)

Pour demarrer automatiquement au boot :

```bash
# Creer le fichier service
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

### Etape 1 : Installer Homebrew (si necessaire)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Etape 2 : Installer les dependances

```bash
brew install git openssl
```

### Etape 3 : Installation

```bash
# Cloner le repository
git clone <url-du-repo> ~/minecraft-server
cd ~/minecraft-server

# Rendre le script executable
chmod +x setup.sh

# Lancer le script
./setup.sh
```

### Etape 4 : Demarrer

```bash
docker compose up -d
```

---

## Installation manuelle

Si vous preferez configurer manuellement :

### 1. Creer le fichier .env

```bash
cp templates/env.template .env
```

### 2. Editer le fichier .env

Remplacez les placeholders par vos valeurs :

```env
# Discord
DISCORD_TOKEN=votre_token_ici
DISCORD_GUILD_ID=votre_guild_id
DISCORD_CLIENT_ID=votre_client_id
DISCORD_CLIENT_SECRET=votre_client_secret

# Generer les mots de passe (Linux/macOS)
RCON_PASSWORD=$(openssl rand -base64 24)
POSTGRES_PASSWORD=$(openssl rand -base64 24)
REDIS_PASSWORD=$(openssl rand -base64 24)
NEXTAUTH_SECRET=$(openssl rand -base64 32)
```

### 3. Creer le docker-compose.yml

```bash
cp templates/docker-compose.template.yml docker-compose.yml
# Remplacer les placeholders
sed -i 's/{{PROJECT_NAME_LOWER}}/monserveur/g' docker-compose.yml
```

### 4. Demarrer les services

```bash
docker compose up -d
```

---

## Configuration post-installation

### Verifier la connexion du bot

```bash
# Voir les logs du bot
docker compose logs bot

# Vous devriez voir :
# [INFO] Bot connecte en tant que VotreBot#1234
# [INFO] Synchronisation des commandes slash...
# [INFO] Pret !
```

### Configurer les channels Discord

1. Utilisez la commande `/notifications configure` dans Discord
2. Selectionnez les channels pour chaque type de notification

### Sauvegarder les secrets

> **IMPORTANT** : Sauvegardez votre fichier `.env` dans un endroit sur !

Les secrets generes sont :
- `RCON_PASSWORD` - Mot de passe RCON Minecraft
- `POSTGRES_PASSWORD` - Mot de passe PostgreSQL
- `REDIS_PASSWORD` - Mot de passe Redis
- `NEXTAUTH_SECRET` - Secret pour les sessions web
- `INTERNAL_API_KEY` - Cle API interne

---

## Troubleshooting installation

### Docker ne demarre pas

**Windows :**
```powershell
# Verifier le service Docker
Get-Service docker

# Redemarrer Docker Desktop
Stop-Process -Name "Docker Desktop" -Force
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

**Linux :**
```bash
# Verifier le service
sudo systemctl status docker

# Redemarrer Docker
sudo systemctl restart docker
```

### Erreur de permission (Linux)

```bash
# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER

# Deconnecter et reconnecter ou utiliser
newgrp docker
```

### Port deja utilise

```bash
# Trouver le processus utilisant le port
# Windows
netstat -ano | findstr :25565

# Linux/macOS
sudo lsof -i :25565

# Tuer le processus ou changer le port dans .env
```

### Le bot ne se connecte pas

1. Verifier le token Discord
2. Verifier que les Intents sont actives dans le Developer Portal
3. Verifier les logs : `docker compose logs bot`

### Erreur de connexion a la base de donnees

```bash
# Verifier que PostgreSQL est demarre
docker compose ps db

# Verifier les logs
docker compose logs db

# Redemarrer le service
docker compose restart db
```

### Minecraft ne demarre pas

```bash
# Verifier les logs
docker compose logs minecraft

# Causes courantes :
# - EULA non acceptee -> verifier EULA=TRUE dans .env
# - Memoire insuffisante -> augmenter MINECRAFT_MEMORY
# - Port deja utilise -> changer MINECRAFT_PORT
```

### Reinitialiser l'installation

```bash
# Arreter tous les services
docker compose down -v

# Supprimer les volumes (ATTENTION : perte de donnees !)
docker volume prune -f

# Relancer l'installation
./setup.sh  # ou .\setup.ps1
```

---

## Prochaines etapes

- [Configuration avancee](configuration.md)
- [Commandes du bot](bot/commands.md)
- [Services Docker](docker/services.md)

---

> **Besoin d'aide ?** Consultez la section [Troubleshooting Docker](docker/troubleshooting.md) pour plus de solutions.
