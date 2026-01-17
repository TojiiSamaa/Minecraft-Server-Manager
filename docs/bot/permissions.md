# Systeme de Permissions

Guide complet du systeme de permissions du bot Discord Minecraft.

---

## Table des matieres

- [Vue d'ensemble](#vue-densemble)
- [Niveaux de permission](#niveaux-de-permission)
- [Configuration des roles Discord](#configuration-des-roles-discord)
- [Commandes par niveau](#commandes-par-niveau)
- [Permissions speciales](#permissions-speciales)
- [Configuration avancee](#configuration-avancee)
- [Troubleshooting](#troubleshooting)

---

## Vue d'ensemble

Le systeme de permissions controle l'acces aux commandes du bot en fonction des roles Discord des utilisateurs.

### Principe de fonctionnement

```
Utilisateur Discord
        │
        ▼
┌───────────────────┐
│ Verification des  │
│    roles Discord  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Determination du  │
│ niveau permission │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Acces autorise   │
│    ou refuse      │
└───────────────────┘
```

### Hierarchie des permissions

```
        OWNER
          │
        ADMIN
          │
      MODERATOR
          │
       PLAYER
```

> **Note :** Chaque niveau herite des permissions des niveaux inferieurs.

---

## Niveaux de permission

### 1. PLAYER (Niveau 0)

**Description :** Niveau par defaut pour tous les membres du serveur Discord.

**Acces :**
- Commandes de consultation (status, liste)
- Informations publiques
- Statistiques personnelles

**Attribution :**
- Automatique pour tous les membres du serveur Discord
- Aucun role specifique requis

**Exemple d'utilisateur :**
- Joueur lambda
- Nouveau membre
- Visiteur

---

### 2. MODERATOR (Niveau 1)

**Description :** Moderateurs du serveur avec acces aux commandes de gestion des joueurs.

**Acces :**
- Toutes les permissions PLAYER
- Kick de joueurs
- Gestion de la whitelist
- Messages serveur
- Teleportation de joueurs

**Attribution :**
- Role Discord configure dans `.env` : `DISCORD_MOD_ROLE_ID`

**Exemple d'utilisateur :**
- Moderateur du serveur
- Helper
- Staff junior

---

### 3. ADMIN (Niveau 2)

**Description :** Administrateurs avec acces complet aux commandes de gestion du serveur.

**Acces :**
- Toutes les permissions MODERATOR
- Demarrage/Arret du serveur
- Bannissement de joueurs
- Configuration des notifications
- Acces console RCON
- Gestion des backups
- Administration du bot

**Attribution :**
- Role Discord configure dans `.env` : `DISCORD_ADMIN_ROLE_ID`

**Exemple d'utilisateur :**
- Administrateur serveur
- Staff senior
- Co-owner

---

### 4. OWNER (Niveau 3)

**Description :** Proprietaire du bot avec acces total sans restriction.

**Acces :**
- Toutes les permissions ADMIN
- Commandes systeme critiques
- Modification de la configuration
- Acces aux logs sensibles
- Bypass de toutes les restrictions

**Attribution :**
- Proprietaire du serveur Discord (automatique)
- ID utilisateur configure dans `.env` : `BOT_OWNER_ID`

**Exemple d'utilisateur :**
- Proprietaire du serveur
- Developpeur du bot

> **Attention :** Le niveau OWNER contourne toutes les verifications de permission. Utilisez-le avec precaution.

---

## Configuration des roles Discord

### Etape 1 : Creer les roles

Dans Discord, creez deux roles :
1. **Administrateur Minecraft** (pour les admins)
2. **Moderateur Minecraft** (pour les moderateurs)

### Etape 2 : Recuperer les IDs des roles

1. Activez le mode developpeur dans Discord
   - Parametres > Avance > Mode developpeur
2. Clic droit sur le role > "Copier l'identifiant"

### Etape 3 : Configurer le fichier .env

```env
# Roles Discord
DISCORD_ADMIN_ROLE_ID=123456789012345678
DISCORD_MOD_ROLE_ID=987654321098765432

# Owner (optionnel, utilise l'owner du serveur par defaut)
BOT_OWNER_ID=111222333444555666
```

### Etape 4 : Redemarrer le bot

```bash
docker compose restart bot
```

### Verification

Utilisez la commande suivante pour verifier vos permissions :

```
/admin permissions check
```

**Reponse :**
```
Vos permissions

Utilisateur: VotreNom#1234
Niveau: ADMIN (2)
Roles: @Administrateur Minecraft

Commandes disponibles: 45/45
```

---

## Commandes par niveau

### PLAYER (Niveau 0)

| Commande | Description |
|----------|-------------|
| `/server status` | Voir le statut du serveur |
| `/players list` | Liste des joueurs connectes |
| `/players info [player]` | Informations sur un joueur |
| `/players whitelist list` | Voir la whitelist |
| `/monitoring stats` | Statistiques de performance |

### MODERATOR (Niveau 1)

| Commande | Description |
|----------|-------------|
| `/players kick [player] [reason]` | Expulser un joueur |
| `/players whitelist add [player]` | Ajouter a la whitelist |
| `/players whitelist remove [player]` | Retirer de la whitelist |
| `/rcon say [message]` | Message serveur |
| `/rcon tp [player] [target]` | Teleporter un joueur |
| `/monitoring alerts` | Voir les alertes |

### ADMIN (Niveau 2)

| Commande | Description |
|----------|-------------|
| `/server start` | Demarrer le serveur |
| `/server stop [delay] [reason]` | Arreter le serveur |
| `/server restart [delay] [reason]` | Redemarrer le serveur |
| `/server backup [type]` | Creer une sauvegarde |
| `/server console [command]` | Executer une commande console |
| `/players ban [player] [reason] [duration]` | Bannir un joueur |
| `/players unban [player]` | Lever un bannissement |
| `/rcon execute [command]` | Commande RCON brute |
| `/rcon give [player] [item] [amount]` | Donner des objets |
| `/rcon gamemode [player] [mode]` | Changer le mode de jeu |
| `/rcon time [value]` | Modifier l'heure |
| `/rcon weather [type]` | Modifier la meteo |
| `/notifications configure` | Configurer les notifications |
| `/notifications toggle [type] [enabled]` | Activer/desactiver |
| `/notifications test [type]` | Tester une notification |
| `/monitoring report [period]` | Generer un rapport |
| `/admin sync` | Synchroniser les commandes |
| `/admin logs [lines] [level]` | Voir les logs |
| `/admin reload` | Recharger la config |

### OWNER (Niveau 3)

| Commande | Description |
|----------|-------------|
| `/admin shutdown` | Arreter completement le bot |
| `/admin eval [code]` | Executer du code Python |
| `/admin config set [key] [value]` | Modifier la configuration |
| `/admin permissions override` | Outrepasser les permissions |

> **Attention :** Les commandes OWNER sont dangereuses et ne doivent etre utilisees qu'en cas de necessite absolue.

---

## Permissions speciales

### Permissions Discord natives

Certaines commandes verifient aussi les permissions Discord natives :

| Permission Discord | Effet |
|-------------------|-------|
| `Administrator` | Equivalent a ADMIN |
| `Manage Server` | Acces aux commandes serveur |
| `Manage Messages` | Peut supprimer des messages du bot |
| `Mention Everyone` | Peut utiliser @everyone dans les commandes |

### Permissions par channel

Vous pouvez restreindre certaines commandes a des channels specifiques :

```env
# Channels autorises pour les commandes admin
ADMIN_COMMAND_CHANNELS=123456789,987654321

# Channel unique pour les commandes sensibles
SENSITIVE_COMMAND_CHANNEL=111222333444555666
```

### Permissions temporaires

Le systeme supporte les permissions temporaires :

```
/admin permissions grant user:@User level:MODERATOR duration:24h
```

Apres 24 heures, l'utilisateur reviendra a son niveau d'origine.

---

## Configuration avancee

### Fichier de configuration des permissions

Creez `config/permissions.json` pour une configuration plus fine :

```json
{
  "levels": {
    "PLAYER": {
      "level": 0,
      "commands": [
        "server status",
        "players list",
        "players info",
        "players whitelist list",
        "monitoring stats"
      ]
    },
    "MODERATOR": {
      "level": 1,
      "roles": ["987654321098765432"],
      "commands": [
        "players kick",
        "players whitelist add",
        "players whitelist remove",
        "rcon say",
        "rcon tp",
        "monitoring alerts"
      ]
    },
    "ADMIN": {
      "level": 2,
      "roles": ["123456789012345678"],
      "commands": ["*"],
      "exclude": ["admin shutdown", "admin eval"]
    },
    "OWNER": {
      "level": 3,
      "users": ["111222333444555666"],
      "commands": ["*"]
    }
  },
  "overrides": {
    "commands": {
      "server backup": {
        "allowed_roles": ["123456789012345678", "backup-role-id"],
        "cooldown": 3600
      }
    },
    "users": {
      "specific-user-id": {
        "level": "ADMIN",
        "reason": "Co-owner du projet"
      }
    }
  }
}
```

### Roles multiples

Un utilisateur peut avoir plusieurs roles. Le niveau le plus eleve est utilise :

```
Utilisateur: Steve#1234
Roles: @Joueur, @Moderateur, @Administrateur

Niveau effectif: ADMIN (le plus eleve)
```

### Logs des permissions

Toutes les verifications de permission sont loguees :

```
[2024-01-15 14:32:15] [PERMISSION] User:Steve#1234 Command:/server stop Level:ADMIN Result:GRANTED
[2024-01-15 14:32:20] [PERMISSION] User:Alex#5678 Command:/server stop Level:PLAYER Result:DENIED
```

Consultez les logs avec :

```
/admin logs level:permission lines:50
```

---

## Troubleshooting

### "Permission refusee" alors que j'ai le bon role

**Causes possibles :**

1. **Le role n'est pas configure dans .env**
   ```bash
   # Verifier la configuration
   cat .env | grep ROLE
   ```

2. **L'ID du role est incorrect**
   - Verifiez l'ID en faisant clic droit > Copier l'identifiant

3. **Le bot n'a pas redémarre apres la configuration**
   ```bash
   docker compose restart bot
   ```

4. **Hierarchie des roles Discord**
   - Le role du bot doit etre au-dessus des roles qu'il gere

### Le proprietaire du serveur n'a pas les permissions OWNER

**Solution :**

Ajoutez explicitement l'ID dans `.env` :

```env
BOT_OWNER_ID=votre-user-id
```

### Les commandes ne s'affichent pas

**Cause :** Les commandes slash ne sont pas synchronisees.

**Solution :**

```
/admin sync
```

Ou redemarrez le bot :

```bash
docker compose restart bot
```

### Un utilisateur a trop de permissions

**Solution :** Verifiez ses roles Discord et retirez les roles inappropries.

Pour verifier les permissions d'un utilisateur :

```
/admin permissions check user:@Utilisateur
```

---

## Liens connexes

- [Commandes du bot](commands.md)
- [Notifications](notifications.md)
- [Configuration generale](../configuration.md)
- [Troubleshooting](../troubleshooting.md)
