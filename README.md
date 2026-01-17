# Gestionnaire de Serveur Minecraft

Une solution complète pour gérer un serveur Minecraft avec un bot Discord, un tableau de bord web et une infrastructure Docker.

## Fonctionnalités

### Bot Discord (Python)
- **Contrôle du serveur** : Démarrer, arrêter, redémarrer via des commandes Discord
- **Commandes RCON** : Exécuter des commandes Minecraft directement depuis Discord
- **Gestion des joueurs** : Liste blanche, bannissements, opérateurs, téléportation
- **Surveillance en temps réel** : TPS, RAM, CPU avec alertes
- **Notifications** : Connexions/déconnexions des joueurs, morts, succès, relais du chat
- **Journalisation** : Système d'audit complet avec Discord + fichiers + base de données

### Tableau de bord web (Next.js)
- **OAuth Discord** : Authentification sécurisée via Discord
- **Gestion du serveur** : Panneau de contrôle visuel
- **Console en direct** : Journaux du serveur en temps réel
- **Éditeur de configuration** : Modifier server.properties depuis le web
- **Gestion des sauvegardes** : Créer, lister, restaurer des sauvegardes

### Infrastructure (Docker)
- **Serveur Minecraft** : Support NeoForge/Forge pour les mods
- **PostgreSQL** : Stockage persistant des données
- **Redis** : Cache et pub/sub
- **Réseaux isolés** : Sécurisé par défaut

## Démarrage rapide

### Prérequis
- Docker & Docker Compose v2
- Git
- Jeton de bot Discord ([Portail développeur Discord](https://discord.com/developers/applications))

### Installation

**Windows (PowerShell)**
```powershell
cd C:\chemin\vers\projet
.\setup.ps1
```

**Linux/macOS (Bash)**
```bash
cd /chemin/vers/projet
chmod +x setup.sh
./setup.sh
```

Le script d'installation va :
1. Vérifier et installer les dépendances automatiquement
2. Demander le nom de votre projet et vos identifiants Discord
3. Générer des mots de passe sécurisés (RCON, PostgreSQL, Redis, etc.)
4. Créer tous les fichiers de configuration
5. Vérifier l'installation

### Lancement

```bash
docker compose up -d
```

## Structure du projet

```
├── bot/                    # Bot Discord (Python)
│   ├── src/
│   │   ├── core/          # Cœur du bot (bot.py, rcon_client.py, etc.)
│   │   ├── cogs/          # Commandes (serveur, rcon, joueurs, etc.)
│   │   └── utils/         # Utilitaires (validateurs, permissions, etc.)
│   ├── Dockerfile
│   └── requirements.txt
├── web/                    # Tableau de bord web (Next.js)
│   ├── src/
│   │   ├── app/           # Routeur App Next.js
│   │   ├── components/    # Composants React
│   │   └── lib/           # Utilitaires
│   ├── Dockerfile
│   └── package.json
├── database/              # Initialisation PostgreSQL
│   └── init/              # Scripts SQL (01-init, 02-tables, etc.)
├── minecraft/             # Données du serveur Minecraft
│   ├── mods/              # Mods NeoForge
│   └── config/            # Configuration du serveur
├── templates/             # Modèles de configuration
├── docs/                  # Documentation complète
├── logs/                  # Journaux de l'application
├── backups/               # Sauvegardes du serveur
├── docker-compose.yml     # Configuration de production
└── .env                   # Variables d'environnement
```

## Configuration

Toute la configuration se fait via les variables d'environnement dans `.env` :

| Variable | Description |
|----------|-------------|
| `PROJECT_NAME` | Le nom de votre projet |
| `DISCORD_TOKEN` | Jeton du bot Discord |
| `DISCORD_GUILD_ID` | ID de votre serveur Discord |
| `RCON_PASSWORD` | Mot de passe RCON généré automatiquement |
| `POSTGRES_PASSWORD` | Mot de passe de la base de données généré automatiquement |

Voir [docs/configuration.md](docs/configuration.md) pour la liste complète.

## Commandes Discord

| Commande | Description | Permission |
|----------|-------------|------------|
| `/server status` | État du serveur | Tout le monde |
| `/server start` | Démarrer le serveur | Admin |
| `/server stop` | Arrêter le serveur | Admin |
| `/rcon execute <cmd>` | Commande RCON | Propriétaire |
| `/players list` | Joueurs en ligne | Tout le monde |
| `/whitelist add <joueur>` | Ajouter à la liste blanche | Admin |
| `/ban <joueur>` | Bannir un joueur | Modérateur |
| `/stats` | Statistiques TPS/RAM/CPU | Tout le monde |
| `/logs view` | Voir les journaux récents | Modérateur |
| `/notifications configure` | Configurer les notifications | Admin |

Voir [docs/bot/commands.md](docs/bot/commands.md) pour toutes les commandes.

## Sécurité

Ce projet inclut plusieurs mesures de sécurité :

- **Validation des entrées** : Toutes les entrées RCON sont validées et assainies
- **Permissions basées sur les rôles** : ID des rôles Discord pour le contrôle d'accès
- **Isolation réseau** : Réseau Docker interne pour les bases de données
- **Rôles SQL** : Rôles PostgreSQL avec privilèges minimaux
- **Masquage des données sensibles** : Mots de passe cachés dans les journaux
- **Limites de ressources** : Limites CPU/RAM sur tous les conteneurs

## Documentation

La documentation complète est disponible dans le dossier [docs/](docs/) :

- [Guide d'installation](docs/installation.md)
- [Référence de configuration](docs/configuration.md)
- [Commandes du bot](docs/bot/commands.md)
- [Système de permissions](docs/bot/permissions.md)
- [Notifications](docs/bot/notifications.md)
- [Services Docker](docs/docker/services.md)
- [Dépannage](docs/troubleshooting.md)

## Développement

```bash
# Démarrer en mode développement
docker compose -f docker-compose.yml -f docker-compose.override.yml up

# Accéder aux services
# - Tableau de bord web : http://localhost:3000
# - Adminer (BDD) : http://localhost:8080
# - Redis Commander : http://localhost:8081
# - Minecraft : localhost:25565
```

## Contribution

Les contributions sont les bienvenues ! Veuillez lire la documentation avant de soumettre une PR.

## Licence

Licence MIT - Voir [LICENSE](LICENSE) pour plus de détails.
