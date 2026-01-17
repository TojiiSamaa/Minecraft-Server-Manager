# Systeme de Notifications

Guide complet du systeme de notifications Discord pour le bot Minecraft.

---

## Table des matieres

- [Vue d'ensemble](#vue-densemble)
- [Les 7 types de notifications](#les-7-types-de-notifications)
- [Configuration via /notifications](#configuration-via-notifications)
- [Personnalisation des embeds](#personnalisation-des-embeds)
- [Mentions et roles](#mentions-et-roles)
- [Cooldowns et rate limiting](#cooldowns-et-rate-limiting)
- [Exemples visuels](#exemples-visuels)
- [Configuration avancee](#configuration-avancee)

---

## Vue d'ensemble

Le systeme de notifications permet d'envoyer automatiquement des messages sur Discord lors d'evenements specifiques sur le serveur Minecraft.

### Fonctionnalites

- **7 types de notifications** configurables independamment
- **Channels personnalisables** par type de notification
- **Mentions** de roles ou utilisateurs
- **Cooldowns** pour eviter le spam
- **Embeds personnalisables** avec couleurs et images
- **Filtres** pour exclure certains joueurs

---

## Les 7 types de notifications

### 1. Connexion joueur (`player_join`)

Envoye lorsqu'un joueur se connecte au serveur.

**Informations affichees :**
- Nom du joueur
- Skin du joueur (tete)
- Heure de connexion
- Nombre de joueurs en ligne

**Exemple d'embed :**
```
+---------------------------------------+
| [Tete]  Steve a rejoint le serveur!   |
|                                       |
| Joueurs en ligne: 5/20                |
| Heure: 14:32                          |
+---------------------------------------+
| Couleur: Vert (#2ecc71)               |
+---------------------------------------+
```

---

### 2. Deconnexion joueur (`player_leave`)

Envoye lorsqu'un joueur quitte le serveur.

**Informations affichees :**
- Nom du joueur
- Duree de la session
- Nombre de joueurs restants

**Exemple d'embed :**
```
+---------------------------------------+
| [Tete]  Steve a quitte le serveur     |
|                                       |
| Temps de jeu: 2h 15m                  |
| Joueurs en ligne: 4/20                |
+---------------------------------------+
| Couleur: Rouge (#e74c3c)              |
+---------------------------------------+
```

---

### 3. Mort de joueur (`player_death`)

Envoye lorsqu'un joueur meurt dans le jeu.

**Informations affichees :**
- Message de mort complet
- Cause de la mort
- Coordonnees (optionnel)
- Dimension (Overworld, Nether, End)

**Exemple d'embed :**
```
+---------------------------------------+
| [Crane] Steve a ete tue par un Zombie |
|                                       |
| Dimension: Overworld                  |
| Position: X: 156, Y: 64, Z: -234      |
+---------------------------------------+
| Couleur: Noir (#2c3e50)               |
+---------------------------------------+
```

---

### 4. Achievement/Advancement (`player_achievement`)

Envoye lorsqu'un joueur debloque un succes.

**Informations affichees :**
- Nom du joueur
- Nom du succes
- Description du succes
- Categorie (Histoire, Aventure, etc.)

**Exemple d'embed :**
```
+---------------------------------------+
| [Trophee] Steve a obtenu [Diamants!]  |
|                                       |
| "Obtenir des diamants"                |
| Categorie: Minecraft                  |
+---------------------------------------+
| Couleur: Or (#f39c12)                 |
+---------------------------------------+
```

---

### 5. Demarrage serveur (`server_start`)

Envoye lorsque le serveur Minecraft demarre.

**Informations affichees :**
- Heure de demarrage
- Version du serveur
- Temps de demarrage
- Adresse de connexion

**Exemple d'embed :**
```
+---------------------------------------+
| [Check] Serveur demarre!              |
|                                       |
| Version: 1.20.4 (NeoForge)            |
| Temps de demarrage: 45 secondes       |
| Adresse: play.monserveur.fr:25565     |
+---------------------------------------+
| Couleur: Vert (#27ae60)               |
+---------------------------------------+
```

---

### 6. Arret serveur (`server_stop`)

Envoye lorsque le serveur s'arrete.

**Informations affichees :**
- Heure d'arret
- Uptime total
- Raison (si specifiee)
- Qui a initie l'arret

**Exemple d'embed :**
```
+---------------------------------------+
| [X] Serveur arrete                    |
|                                       |
| Uptime: 3 jours 14 heures             |
| Raison: Maintenance planifiee         |
| Par: Admin#1234                       |
+---------------------------------------+
| Couleur: Orange (#e67e22)             |
+---------------------------------------+
```

---

### 7. Alertes performance (`performance_alert`)

Envoye lors de problemes de performance.

**Types d'alertes :**
- TPS bas (< 18)
- RAM elevee (> 80%)
- CPU eleve (> 90%)
- Latence RCON elevee

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

Cette commande ouvre un menu interactif avec des boutons et menus deroulants.

### Options du menu

1. **Selectionner le type** - Choisir quel type de notification configurer
2. **Definir le channel** - Selectionner le channel de destination
3. **Activer/Desactiver** - Toggle on/off
4. **Configurer les mentions** - Ajouter roles/users a mentionner
5. **Regler le cooldown** - Temps minimum entre notifications

### Exemples de configuration

#### Configurer les notifications de connexion

```
/notifications configure
> Selectionner: player_join
> Channel: #connexions
> Mentions: @Joueurs
> Cooldown: 0 secondes
> Activer: Oui
```

#### Configurer les alertes performance

```
/notifications configure
> Selectionner: performance_alert
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
    "color": 0x2ecc71,  # Couleur en hexadecimal
    "thumbnail": {
        "url": "URL de l'image miniature"
    },
    "fields": [
        {"name": "Champ 1", "value": "Valeur 1", "inline": True},
        {"name": "Champ 2", "value": "Valeur 2", "inline": True}
    ],
    "footer": {
        "text": "Texte du footer",
        "icon_url": "URL icone"
    },
    "timestamp": "2024-01-15T14:32:00Z"
}
```

### Couleurs par defaut

| Type | Couleur | Code Hex |
|------|---------|----------|
| `player_join` | Vert | `#2ecc71` |
| `player_leave` | Rouge | `#e74c3c` |
| `player_death` | Noir | `#2c3e50` |
| `player_achievement` | Or | `#f39c12` |
| `server_start` | Vert fonce | `#27ae60` |
| `server_stop` | Orange | `#e67e22` |
| `performance_alert` | Rouge fonce | `#c0392b` |

### Personnalisation via la base de donnees

Les embeds peuvent etre personnalises dans la base de donnees :

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

## Mentions et roles

### Configurer les mentions

```
/notifications configure
> Mentions: @Admin, @Moderateur
```

### Types de mentions

| Type | Syntaxe | Exemple |
|------|---------|---------|
| Role | `@role` | `@Admin` |
| Utilisateur | `@user` | `@User#1234` |
| Everyone | `@everyone` | Tout le monde |
| Here | `@here` | Membres en ligne |

> **Attention :** L'utilisation de `@everyone` et `@here` necessite les permissions appropriees.

### Mentions conditionnelles

Certaines mentions peuvent etre conditionnelles :

```python
# Mentionner @Admin uniquement si TPS < 15
if alert_type == "performance" and tps < 15:
    mention = "@Admin"
```

---

## Cooldowns et rate limiting

### Qu'est-ce qu'un cooldown ?

Le cooldown definit le temps minimum entre deux notifications du meme type.

### Configuration des cooldowns

| Type | Cooldown recommande | Raison |
|------|---------------------|--------|
| `player_join` | 0s | Chaque connexion est importante |
| `player_leave` | 0s | Chaque deconnexion est importante |
| `player_death` | 30s | Eviter le spam lors de morts repetees |
| `player_achievement` | 0s | Les succes sont rares |
| `server_start` | 0s | Evenement rare |
| `server_stop` | 0s | Evenement rare |
| `performance_alert` | 300s | Eviter le spam d'alertes |

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
┌─────────────────────────────────────────────────┐
│ 🟢 Steve a rejoint le serveur!                  │
├─────────────────────────────────────────────────┤
│ ┌──────┐                                        │
│ │      │  Joueurs en ligne                      │
│ │ Skin │  5 / 20                                │
│ │      │                                        │
│ └──────┘  Premiere visite: Non                  │
│           Dernier temps de jeu: 156h            │
├─────────────────────────────────────────────────┤
│ Aujourd'hui a 14:32                             │
└─────────────────────────────────────────────────┘
```

### Notification de mort

```
┌─────────────────────────────────────────────────┐
│ ☠️ Steve a ete tue par Zombie                    │
├─────────────────────────────────────────────────┤
│                                                 │
│  Dimension    │ Overworld                       │
│  Position     │ X: 156, Y: 64, Z: -234          │
│  Biome        │ Plains                          │
│                                                 │
├─────────────────────────────────────────────────┤
│ C'est sa 42eme mort sur le serveur              │
└─────────────────────────────────────────────────┘
```

### Notification d'achievement

```
┌─────────────────────────────────────────────────┐
│ 🏆 Steve a obtenu un succes!                    │
├─────────────────────────────────────────────────┤
│                                                 │
│  [Diamants!]                                    │
│  Obtenir des diamants                           │
│                                                 │
│  Categorie: Minecraft                           │
│  Rarete: 60% des joueurs                        │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Alerte performance

```
┌─────────────────────────────────────────────────┐
│ ⚠️ ALERTE PERFORMANCE                           │
├─────────────────────────────────────────────────┤
│                                                 │
│  TPS         │ 15.2 ⚠️ (Normal: 20)             │
│  RAM         │ 3.4 GB / 4 GB (85%) ⚠️           │
│  CPU         │ 78%                              │
│  Joueurs     │ 18/20                            │
│                                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 85%          │
│                                                 │
├─────────────────────────────────────────────────┤
│ @Admin - Action recommandee                     │
└─────────────────────────────────────────────────┘
```

---

## Configuration avancee

### Fichier de configuration

Les notifications peuvent aussi etre configurees via le fichier `config/notifications.json` :

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

### Webhooks personnalises

Pour plus de controle, vous pouvez utiliser des webhooks :

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
- [Systeme de permissions](permissions.md)
- [Configuration generale](../configuration.md)
- [Troubleshooting](../troubleshooting.md)
