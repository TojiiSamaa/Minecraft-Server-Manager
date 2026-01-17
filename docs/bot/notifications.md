# Système de Notifications

Guide complet du système de notifications Discord pour le bot Minecraft.

---

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Les 7 types de notifications](#les-7-types-de-notifications)
- [Configuration via /notifications](#configuration-via-notifications)
- [Personnalisation des embeds](#personnalisation-des-embeds)
- [Mentions et rôles](#mentions-et-rôles)
- [Cooldowns et rate limiting](#cooldowns-et-rate-limiting)
- [Exemples visuels](#exemples-visuels)
- [Configuration avancée](#configuration-avancée)

---

## Vue d'ensemble

Le système de notifications permet d'envoyer automatiquement des messages sur Discord lors d'événements spécifiques sur le serveur Minecraft.

### Fonctionnalités

- **7 types de notifications** configurables indépendamment
- **Channels personnalisables** par type de notification
- **Mentions** de rôles ou utilisateurs
- **Cooldowns** pour éviter le spam
- **Embeds personnalisables** avec couleurs et images
- **Filtres** pour exclure certains joueurs

---

## Les 7 types de notifications

### 1. Connexion joueur (`player_join`)

Envoyé lorsqu'un joueur se connecte au serveur.

**Informations affichées :**
- Nom du joueur
- Skin du joueur (tête)
- Heure de connexion
- Nombre de joueurs en ligne

**Exemple d'embed :**
```
+---------------------------------------+
| [Tête]  Steve a rejoint le serveur!   |
|                                       |
| Joueurs en ligne: 5/20                |
| Heure: 14:32                          |
+---------------------------------------+
| Couleur: Vert (#2ecc71)               |
+---------------------------------------+
```

---

### 2. Déconnexion joueur (`player_leave`)

Envoyé lorsqu'un joueur quitte le serveur.

**Informations affichées :**
- Nom du joueur
- Durée de la session
- Nombre de joueurs restants

**Exemple d'embed :**
```
+---------------------------------------+
| [Tête]  Steve a quitté le serveur     |
|                                       |
| Temps de jeu: 2h 15m                  |
| Joueurs en ligne: 4/20                |
+---------------------------------------+
| Couleur: Rouge (#e74c3c)              |
+---------------------------------------+
```

---

### 3. Mort de joueur (`player_death`)

Envoyé lorsqu'un joueur meurt dans le jeu.

**Informations affichées :**
- Message de mort complet
- Cause de la mort
- Coordonnées (optionnel)
- Dimension (Overworld, Nether, End)

**Exemple d'embed :**
```
+---------------------------------------+
| [Crâne] Steve a été tué par un Zombie |
|                                       |
| Dimension: Overworld                  |
| Position: X: 156, Y: 64, Z: -234      |
+---------------------------------------+
| Couleur: Noir (#2c3e50)               |
+---------------------------------------+
```

---

### 4. Achievement/Advancement (`player_achievement`)

Envoyé lorsqu'un joueur débloque un succès.

**Informations affichées :**
- Nom du joueur
- Nom du succès
- Description du succès
- Catégorie (Histoire, Aventure, etc.)

**Exemple d'embed :**
```
+---------------------------------------+
| [Trophée] Steve a obtenu [Diamants!]  |
|                                       |
| "Obtenir des diamants"                |
| Catégorie: Minecraft                  |
+---------------------------------------+
| Couleur: Or (#f39c12)                 |
+---------------------------------------+
```

---

### 5. Démarrage serveur (`server_start`)

Envoyé lorsque le serveur Minecraft démarre.

**Informations affichées :**
- Heure de démarrage
- Version du serveur
- Temps de démarrage
- Adresse de connexion

**Exemple d'embed :**
```
+---------------------------------------+
| [Check] Serveur démarré!              |
|                                       |
| Version: 1.20.4 (NeoForge)            |
| Temps de démarrage: 45 secondes       |
| Adresse: play.monserveur.fr:25565     |
+---------------------------------------+
| Couleur: Vert (#27ae60)               |
+---------------------------------------+
```

---

### 6. Arrêt serveur (`server_stop`)

Envoyé lorsque le serveur s'arrête.

**Informations affichées :**
- Heure d'arrêt
- Uptime total
- Raison (si spécifiée)
- Qui a initié l'arrêt

**Exemple d'embed :**
```
+---------------------------------------+
| [X] Serveur arrêté                    |
|                                       |
| Uptime: 3 jours 14 heures             |
| Raison: Maintenance planifiée         |
| Par: Admin#1234                       |
+---------------------------------------+
| Couleur: Orange (#e67e22)             |
+---------------------------------------+
```

---

### 7. Alertes performance (`performance_alert`)

Envoyé lors de problèmes de performance.

**Types d'alertes :**
- TPS bas (< 18)
- RAM élevée (> 80%)
- CPU élevé (> 90%)
- Latence RCON élevée

**Exemple d'embed :**
```
+---------------------------------------+
| [Warning] Alerte Performance          |
|                                       |
| TPS: 15.2 (Critique < 15)             |
| RAM: 85% (3.4/4 GB)                   |
| CPU: 78%                              |
|                                       |
| Joueurs en ligne: 18                  |
+---------------------------------------+
| Couleur: Rouge (#c0392b)              |
+---------------------------------------+
```

---

## Configuration via /notifications

### Commande principale

```
/notifications configure
```

Cette commande ouvre un menu interactif avec des boutons et menus déroulants.

### Options du menu

1. **Sélectionner le type** - Choisir quel type de notification configurer
2. **Définir le channel** - Sélectionner le channel de destination
3. **Activer/Désactiver** - Toggle on/off
4. **Configurer les mentions** - Ajouter rôles/users à mentionner
5. **Régler le cooldown** - Temps minimum entre notifications

### Exemples de configuration

#### Configurer les notifications de connexion

```
/notifications configure
> Sélectionner: player_join
> Channel: #connexions
> Mentions: @Joueurs
> Cooldown: 0 secondes
> Activer: Oui
```

#### Configurer les alertes performance

```
/notifications configure
> Sélectionner: performance_alert
> Channel: #alertes-admin
> Mentions: @Admin
> Cooldown: 300 secondes (5 min)
> Activer: Oui
```

### Configuration rapide avec /notifications toggle

```
/notifications toggle type:player_death enabled:true
```

### Tester une notification

```
/notifications test type:player_join
```

---

## Personnalisation des embeds

### Structure d'un embed

```python
embed = {
    "title": "Titre de la notification",
    "description": "Description principale",
    "color": 0x2ecc71,  # Couleur en hexadécimal
    "thumbnail": {
        "url": "URL de l'image miniature"
    },
    "fields": [
        {"name": "Champ 1", "value": "Valeur 1", "inline": True},
        {"name": "Champ 2", "value": "Valeur 2", "inline": True}
    ],
    "footer": {
        "text": "Texte du footer",
        "icon_url": "URL icône"
    },
    "timestamp": "2024-01-15T14:32:00Z"
}
```

### Couleurs par défaut

| Type | Couleur | Code Hex |
|------|---------|----------|
| `player_join` | Vert | `#2ecc71` |
| `player_leave` | Rouge | `#e74c3c` |
| `player_death` | Noir | `#2c3e50` |
| `player_achievement` | Or | `#f39c12` |
| `server_start` | Vert foncé | `#27ae60` |
| `server_stop` | Orange | `#e67e22` |
| `performance_alert` | Rouge foncé | `#c0392b` |

### Personnalisation via la base de données

Les embeds peuvent être personnalisés dans la base de données :

```sql
UPDATE notification_settings
SET embed_config = '{
    "color": "#ff6b6b",
    "show_coordinates": false,
    "show_timestamp": true
}'
WHERE notification_type = 'player_death';
```

---

## Mentions et rôles

### Configurer les mentions

```
/notifications configure
> Mentions: @Admin, @Modérateur
```

### Types de mentions

| Type | Syntaxe | Exemple |
|------|---------|---------|
| Rôle | `@role` | `@Admin` |
| Utilisateur | `@user` | `@User#1234` |
| Everyone | `@everyone` | Tout le monde |
| Here | `@here` | Membres en ligne |

> **Attention :** L'utilisation de `@everyone` et `@here` nécessite les permissions appropriées.

### Mentions conditionnelles

Certaines mentions peuvent être conditionnelles :

```python
# Mentionner @Admin uniquement si TPS < 15
if alert_type == "performance" and tps < 15:
    mention = "@Admin"
```

---

## Cooldowns et rate limiting

### Qu'est-ce qu'un cooldown ?

Le cooldown définit le temps minimum entre deux notifications du même type.

### Configuration des cooldowns

| Type | Cooldown recommandé | Raison |
|------|---------------------|--------|
| `player_join` | 0s | Chaque connexion est importante |
| `player_leave` | 0s | Chaque déconnexion est importante |
| `player_death` | 30s | Éviter le spam lors de morts répétées |
| `player_achievement` | 0s | Les succès sont rares |
| `server_start` | 0s | Événement rare |
| `server_stop` | 0s | Événement rare |
| `performance_alert` | 300s | Éviter le spam d'alertes |

### Configurer un cooldown

```
/notifications configure
> Type: player_death
> Cooldown: 30
```

### Rate limiting global

Le bot inclut un rate limiter global pour respecter les limites Discord :

- Maximum 5 messages par seconde par channel
- Maximum 50 messages par minute par channel

---

## Exemples visuels

### Notification de connexion

```
+---------------------------------------------------+
| Steve a rejoint le serveur!                       |
+---------------------------------------------------+
| +------+                                          |
| |      |  Joueurs en ligne                        |
| | Skin |  5 / 20                                  |
| |      |                                          |
| +------+  Première visite: Non                    |
|           Dernier temps de jeu: 156h              |
+---------------------------------------------------+
| Aujourd'hui à 14:32                               |
+---------------------------------------------------+
```

### Notification de mort

```
+---------------------------------------------------+
| Steve a été tué par Zombie                        |
+---------------------------------------------------+
|                                                   |
|  Dimension    | Overworld                         |
|  Position     | X: 156, Y: 64, Z: -234            |
|  Biome        | Plains                            |
|                                                   |
+---------------------------------------------------+
| C'est sa 42ème mort sur le serveur                |
+---------------------------------------------------+
```

### Notification d'achievement

```
+---------------------------------------------------+
| Steve a obtenu un succès!                         |
+---------------------------------------------------+
|                                                   |
|  [Diamants!]                                      |
|  Obtenir des diamants                             |
|                                                   |
|  Catégorie: Minecraft                             |
|  Rareté: 60% des joueurs                          |
|                                                   |
+---------------------------------------------------+
```

### Alerte performance

```
+---------------------------------------------------+
| ALERTE PERFORMANCE                                |
+---------------------------------------------------+
|                                                   |
|  TPS         | 15.2 (Normal: 20)                  |
|  RAM         | 3.4 GB / 4 GB (85%)                |
|  CPU         | 78%                                |
|  Joueurs     | 18/20                              |
|                                                   |
+---------------------------------------------------+
| @Admin - Action recommandée                       |
+---------------------------------------------------+
```

---

## Configuration avancée

### Fichier de configuration

Les notifications peuvent aussi être configurées via le fichier `config/notifications.json` :

```json
{
  "player_join": {
    "enabled": true,
    "channel_id": "123456789012345678",
    "mentions": ["role:Admin"],
    "cooldown": 0,
    "embed": {
      "color": "#2ecc71",
      "show_skin": true,
      "show_stats": true
    }
  },
  "player_death": {
    "enabled": true,
    "channel_id": "123456789012345678",
    "mentions": [],
    "cooldown": 30,
    "embed": {
      "color": "#2c3e50",
      "show_coordinates": true,
      "show_death_count": true
    },
    "filters": {
      "exclude_players": ["Bot", "Admin"]
    }
  },
  "performance_alert": {
    "enabled": true,
    "channel_id": "123456789012345678",
    "mentions": ["role:Admin"],
    "cooldown": 300,
    "thresholds": {
      "tps_warning": 18,
      "tps_critical": 15,
      "ram_warning": 80,
      "ram_critical": 90
    }
  }
}
```

### Variables disponibles dans les templates

| Variable | Description | Exemple |
|----------|-------------|---------|
| `{player}` | Nom du joueur | Steve |
| `{uuid}` | UUID du joueur | a1b2c3... |
| `{online}` | Joueurs en ligne | 5 |
| `{max}` | Max joueurs | 20 |
| `{time}` | Heure actuelle | 14:32 |
| `{date}` | Date actuelle | 15/01/2024 |
| `{server}` | Nom du serveur | MonServeur |
| `{version}` | Version MC | 1.20.4 |

### Webhooks personnalisés

Pour plus de contrôle, vous pouvez utiliser des webhooks :

```json
{
  "player_join": {
    "use_webhook": true,
    "webhook_url": "https://discord.com/api/webhooks/xxx/yyy",
    "webhook_name": "Minecraft Server",
    "webhook_avatar": "https://example.com/avatar.png"
  }
}
```

---

## Liens connexes

- [Commandes du bot](commands.md)
- [Système de permissions](permissions.md)
- [Configuration générale](../configuration.md)
- [Dépannage](../troubleshooting.md)
