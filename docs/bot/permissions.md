# Système de Permissions

Guide complet du système de permissions du bot Discord Minecraft.

---

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Niveaux de permission](#niveaux-de-permission)
- [Configuration des rôles Discord](#configuration-des-rôles-discord)
- [Commandes par niveau](#commandes-par-niveau)
- [Permissions spéciales](#permissions-spéciales)
- [Configuration avancée](#configuration-avancée)
- [Dépannage](#dépannage)

---

## Vue d'ensemble

Le système de permissions contrôle l'accès aux commandes du bot en fonction des rôles Discord des utilisateurs.

### Principe de fonctionnement

```
Utilisateur Discord
        |
        v
+-------------------+
| Vérification des  |
|    rôles Discord  |
+---------+---------+
          |
          v
+-------------------+
| Détermination du  |
| niveau permission |
+---------+---------+
          |
          v
+-------------------+
|  Accès autorisé   |
|    ou refusé      |
+-------------------+
```

### Hiérarchie des permissions

```
        OWNER
          |
        ADMIN
          |
      MODERATOR
          |
       PLAYER
```

> **Note :** Chaque niveau hérite des permissions des niveaux inférieurs.

---

## Niveaux de permission

### 1. PLAYER (Niveau 0)

**Description :** Niveau par défaut pour tous les membres du serveur Discord.

**Accès :**
- Commandes de consultation (status, liste)
- Informations publiques
- Statistiques personnelles

**Attribution :**
- Automatique pour tous les membres du serveur Discord
- Aucun rôle spécifique requis

**Exemple d'utilisateur :**
- Joueur lambda
- Nouveau membre
- Visiteur

---

### 2. MODERATOR (Niveau 1)

**Description :** Modérateurs du serveur avec accès aux commandes de gestion des joueurs.

**Accès :**
- Toutes les permissions PLAYER
- Kick de joueurs
- Gestion de la whitelist
- Messages serveur
- Téléportation de joueurs

**Attribution :**
- Rôle Discord configuré dans `.env` : `DISCORD_MOD_ROLE_ID`

**Exemple d'utilisateur :**
- Modérateur du serveur
- Helper
- Staff junior

---

### 3. ADMIN (Niveau 2)

**Description :** Administrateurs avec accès complet aux commandes de gestion du serveur.

**Accès :**
- Toutes les permissions MODERATOR
- Démarrage/Arrêt du serveur
- Bannissement de joueurs
- Configuration des notifications
- Accès console RCON
- Gestion des backups
- Administration du bot

**Attribution :**
- Rôle Discord configuré dans `.env` : `DISCORD_ADMIN_ROLE_ID`

**Exemple d'utilisateur :**
- Administrateur serveur
- Staff senior
- Co-owner

---

### 4. OWNER (Niveau 3)

**Description :** Propriétaire du bot avec accès total sans restriction.

**Accès :**
- Toutes les permissions ADMIN
- Commandes système critiques
- Modification de la configuration
- Accès aux logs sensibles
- Bypass de toutes les restrictions

**Attribution :**
- Propriétaire du serveur Discord (automatique)
- ID utilisateur configuré dans `.env` : `BOT_OWNER_ID`

**Exemple d'utilisateur :**
- Propriétaire du serveur
- Développeur du bot

> **Attention :** Le niveau OWNER contourne toutes les vérifications de permission. Utilisez-le avec précaution.

---

## Configuration des rôles Discord

### Étape 1 : Créer les rôles

Dans Discord, créez deux rôles :
1. **Administrateur Minecraft** (pour les admins)
2. **Modérateur Minecraft** (pour les modérateurs)

### Étape 2 : Récupérer les IDs des rôles

1. Activez le mode développeur dans Discord
   - Paramètres > Avancé > Mode développeur
2. Clic droit sur le rôle > "Copier l'identifiant"

### Étape 3 : Configurer le fichier .env

```env
# Rôles Discord
DISCORD_ADMIN_ROLE_ID=123456789012345678
DISCORD_MOD_ROLE_ID=987654321098765432

# Owner (optionnel, utilise l'owner du serveur par défaut)
BOT_OWNER_ID=111222333444555666
```

### Étape 4 : Redémarrer le bot

```bash
docker compose restart bot
```

### Vérification

Utilisez la commande suivante pour vérifier vos permissions :

```
/admin permissions check
```

**Réponse :**
```
Vos permissions

Utilisateur: VotreNom#1234
Niveau: ADMIN (2)
Rôles: @Administrateur Minecraft

Commandes disponibles: 45/45
```

---

## Commandes par niveau

### PLAYER (Niveau 0)

| Commande | Description |
|----------|-------------|
| `/server status` | Voir le statut du serveur |
| `/players list` | Liste des joueurs connectés |
| `/players info [player]` | Informations sur un joueur |
| `/players whitelist list` | Voir la whitelist |
| `/monitoring stats` | Statistiques de performance |

### MODERATOR (Niveau 1)

| Commande | Description |
|----------|-------------|
| `/players kick [player] [reason]` | Expulser un joueur |
| `/players whitelist add [player]` | Ajouter à la whitelist |
| `/players whitelist remove [player]` | Retirer de la whitelist |
| `/rcon say [message]` | Message serveur |
| `/rcon tp [player] [target]` | Téléporter un joueur |
| `/monitoring alerts` | Voir les alertes |

### ADMIN (Niveau 2)

| Commande | Description |
|----------|-------------|
| `/server start` | Démarrer le serveur |
| `/server stop [delay] [reason]` | Arrêter le serveur |
| `/server restart [delay] [reason]` | Redémarrer le serveur |
| `/server backup [type]` | Créer une sauvegarde |
| `/server console [command]` | Exécuter une commande console |
| `/players ban [player] [reason] [duration]` | Bannir un joueur |
| `/players unban [player]` | Lever un bannissement |
| `/rcon execute [command]` | Commande RCON brute |
| `/rcon give [player] [item] [amount]` | Donner des objets |
| `/rcon gamemode [player] [mode]` | Changer le mode de jeu |
| `/rcon time [value]` | Modifier l'heure |
| `/rcon weather [type]` | Modifier la météo |
| `/notifications configure` | Configurer les notifications |
| `/notifications toggle [type] [enabled]` | Activer/désactiver |
| `/notifications test [type]` | Tester une notification |
| `/monitoring report [period]` | Générer un rapport |
| `/admin sync` | Synchroniser les commandes |
| `/admin logs [lines] [level]` | Voir les logs |
| `/admin reload` | Recharger la config |

### OWNER (Niveau 3)

| Commande | Description |
|----------|-------------|
| `/admin shutdown` | Arrêter complètement le bot |
| `/admin eval [code]` | Exécuter du code Python |
| `/admin config set [key] [value]` | Modifier la configuration |
| `/admin permissions override` | Outrepasser les permissions |

> **Attention :** Les commandes OWNER sont dangereuses et ne doivent être utilisées qu'en cas de nécessité absolue.

---

## Permissions spéciales

### Permissions Discord natives

Certaines commandes vérifient aussi les permissions Discord natives :

| Permission Discord | Effet |
|-------------------|-------|
| `Administrator` | Équivalent à ADMIN |
| `Manage Server` | Accès aux commandes serveur |
| `Manage Messages` | Peut supprimer des messages du bot |
| `Mention Everyone` | Peut utiliser @everyone dans les commandes |

### Permissions par channel

Vous pouvez restreindre certaines commandes à des channels spécifiques :

```env
# Channels autorisés pour les commandes admin
ADMIN_COMMAND_CHANNELS=123456789,987654321

# Channel unique pour les commandes sensibles
SENSITIVE_COMMAND_CHANNEL=111222333444555666
```

### Permissions temporaires

Le système supporte les permissions temporaires :

```
/admin permissions grant user:@User level:MODERATOR duration:24h
```

Après 24 heures, l'utilisateur reviendra à son niveau d'origine.

---

## Configuration avancée

### Fichier de configuration des permissions

Créez `config/permissions.json` pour une configuration plus fine :

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

### Rôles multiples

Un utilisateur peut avoir plusieurs rôles. Le niveau le plus élevé est utilisé :

```
Utilisateur: Steve#1234
Rôles: @Joueur, @Modérateur, @Administrateur

Niveau effectif: ADMIN (le plus élevé)
```

### Logs des permissions

Toutes les vérifications de permission sont loguées :

```
[2024-01-15 14:32:15] [PERMISSION] User:Steve#1234 Command:/server stop Level:ADMIN Result:GRANTED
[2024-01-15 14:32:20] [PERMISSION] User:Alex#5678 Command:/server stop Level:PLAYER Result:DENIED
```

Consultez les logs avec :

```
/admin logs level:permission lines:50
```

---

## Dépannage

### "Permission refusée" alors que j'ai le bon rôle

**Causes possibles :**

1. **Le rôle n'est pas configuré dans .env**
   ```bash
   # Vérifier la configuration
   cat .env | grep ROLE
   ```

2. **L'ID du rôle est incorrect**
   - Vérifiez l'ID en faisant clic droit > Copier l'identifiant

3. **Le bot n'a pas redémarré après la configuration**
   ```bash
   docker compose restart bot
   ```

4. **Hiérarchie des rôles Discord**
   - Le rôle du bot doit être au-dessus des rôles qu'il gère

### Le propriétaire du serveur n'a pas les permissions OWNER

**Solution :**

Ajoutez explicitement l'ID dans `.env` :

```env
BOT_OWNER_ID=votre-user-id
```

### Les commandes ne s'affichent pas

**Cause :** Les commandes slash ne sont pas synchronisées.

**Solution :**

```
/admin sync
```

Ou redémarrez le bot :

```bash
docker compose restart bot
```

### Un utilisateur a trop de permissions

**Solution :** Vérifiez ses rôles Discord et retirez les rôles inappropriés.

Pour vérifier les permissions d'un utilisateur :

```
/admin permissions check user:@Utilisateur
```

---

## Liens connexes

- [Commandes du bot](commands.md)
- [Notifications](notifications.md)
- [Configuration générale](../configuration.md)
- [Dépannage](../troubleshooting.md)
