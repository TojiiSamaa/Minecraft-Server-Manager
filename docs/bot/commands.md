# Commandes Slash du Bot Discord

Liste complète de toutes les commandes slash disponibles avec exemples d'utilisation.

---

## Table des matières

- [Commandes Serveur](#commandes-serveur)
- [Commandes Joueurs](#commandes-joueurs)
- [Commandes RCON](#commandes-rcon)
- [Commandes Notifications](#commandes-notifications)
- [Commandes Monitoring](#commandes-monitoring)
- [Commandes Administration](#commandes-administration)
- [Référence rapide](#référence-rapide)

---

## Commandes Serveur

### `/server status`

Affiche le statut actuel du serveur Minecraft.

**Permission requise :** `PLAYER`

**Exemple d'utilisation :**
```
/server status
```

**Réponse :**
```
Statut du Serveur

État: En ligne
Version: 1.20.4 (NeoForge)
Joueurs: 5/20
TPS: 19.8

Mémoire: 2.1 GB / 4 GB (52%)
Uptime: 3j 14h 25m
```

<!-- [Screenshot placeholder: server-status.png] -->

---

### `/server start`

Démarre le serveur Minecraft.

**Permission requise :** `ADMIN`

**Exemple d'utilisation :**
```
/server start
```

**Réponse :**
```
Démarrage du serveur en cours...
Le serveur devrait être disponible dans quelques instants.
```

---

### `/server stop`

Arrête proprement le serveur Minecraft.

**Permission requise :** `ADMIN`

**Options :**
| Option | Description | Défaut |
|--------|-------------|--------|
| `delay` | Délai avant arrêt (secondes) | 60 |
| `reason` | Raison de l'arrêt | - |

**Exemple d'utilisation :**
```
/server stop delay:30 reason:Maintenance
```

**Réponse :**
```
Arrêt programmé dans 30 secondes.
Les joueurs ont été prévenus.
Raison: Maintenance
```

---

### `/server restart`

Redémarre le serveur Minecraft.

**Permission requise :** `ADMIN`

**Options :**
| Option | Description | Défaut |
|--------|-------------|--------|
| `delay` | Délai avant redémarrage | 60 |
| `reason` | Raison du redémarrage | - |

**Exemple d'utilisation :**
```
/server restart delay:120 reason:Mise à jour des plugins
```

---

### `/server backup`

Crée une sauvegarde manuelle du serveur.

**Permission requise :** `ADMIN`

**Options :**
| Option | Description | Défaut |
|--------|-------------|--------|
| `type` | Type de backup | `full` |
| `notify` | Notifier sur Discord | `true` |

**Types disponibles :**
- `full` : Sauvegarde complète (mondes + configs + base de données)
- `worlds` : Mondes uniquement
- `database` : Base de données uniquement
- `quick` : Sauvegarde rapide (monde principal)

**Exemple d'utilisation :**
```
/server backup type:full
```

---

### `/server console`

Envoie une commande directement à la console du serveur.

**Permission requise :** `ADMIN`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `command` | Commande à exécuter | Oui |

**Exemple d'utilisation :**
```
/server console command:say Bonjour à tous!
```

---

## Commandes Joueurs

### `/players list`

Affiche la liste des joueurs connectés.

**Permission requise :** `PLAYER`

**Exemple d'utilisation :**
```
/players list
```

**Réponse :**
```
Joueurs en ligne (5/20)

Steve - En ligne depuis 2h 15m
Alex - En ligne depuis 45m
Notch - En ligne depuis 1h 30m
Herobrine - En ligne depuis 3h 10m
Jeb - En ligne depuis 20m
```

---

### `/players info`

Affiche les informations d'un joueur.

**Permission requise :** `PLAYER`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `player` | Nom du joueur | Oui |

**Exemple d'utilisation :**
```
/players info player:Steve
```

**Réponse :**
```
Informations - Steve

UUID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Première connexion: 15/01/2024
Dernière connexion: En ligne maintenant
Temps de jeu total: 156h 32m

Statistiques
  Morts: 42
  Kills: 128
  Blocs cassés: 15,432
  Blocs placés: 12,876
```

---

### `/players kick`

Expulse un joueur du serveur.

**Permission requise :** `MODERATOR`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `player` | Nom du joueur | Oui |
| `reason` | Raison de l'expulsion | Non |

**Exemple d'utilisation :**
```
/players kick player:Griefer reason:Comportement inapproprié
```

---

### `/players ban`

Bannit un joueur du serveur.

**Permission requise :** `ADMIN`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `player` | Nom du joueur | Oui |
| `reason` | Raison du bannissement | Non |
| `duration` | Durée du ban | Non (permanent) |

**Exemple d'utilisation :**
```
/players ban player:Hacker reason:Utilisation de cheats duration:7d
```

---

### `/players unban`

Lève le bannissement d'un joueur.

**Permission requise :** `ADMIN`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `player` | Nom du joueur | Oui |

**Exemple d'utilisation :**
```
/players unban player:ReformedPlayer
```

---

### `/players whitelist add`

Ajoute un joueur à la whitelist.

**Permission requise :** `MODERATOR`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `player` | Nom du joueur | Oui |

**Exemple d'utilisation :**
```
/players whitelist add player:NouveauJoueur
```

---

### `/players whitelist remove`

Retire un joueur de la whitelist.

**Permission requise :** `MODERATOR`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `player` | Nom du joueur | Oui |

**Exemple d'utilisation :**
```
/players whitelist remove player:AncienJoueur
```

---

### `/players whitelist list`

Affiche la liste des joueurs whitelistés.

**Permission requise :** `PLAYER`

**Exemple d'utilisation :**
```
/players whitelist list
```

---

## Commandes RCON

### `/rcon execute`

Exécute une commande RCON personnalisée.

**Permission requise :** `ADMIN`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `command` | Commande RCON | Oui |

**Exemple d'utilisation :**
```
/rcon execute command:give @a minecraft:diamond 64
```

> **Attention :** Cette commande permet d'exécuter n'importe quelle commande Minecraft. Utilisez-la avec précaution.

---

### `/rcon say`

Envoie un message à tous les joueurs.

**Permission requise :** `MODERATOR`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `message` | Message à envoyer | Oui |

**Exemple d'utilisation :**
```
/rcon say message:Redémarrage du serveur dans 10 minutes!
```

---

### `/rcon tp`

Téléporte un joueur.

**Permission requise :** `MODERATOR`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `player` | Joueur à téléporter | Oui |
| `target` | Destination (joueur ou coords) | Oui |

**Exemple d'utilisation :**
```
/rcon tp player:Steve target:Alex
/rcon tp player:Steve target:100 64 200
```

---

### `/rcon give`

Donne des objets à un joueur.

**Permission requise :** `ADMIN`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `player` | Joueur destinataire | Oui |
| `item` | ID de l'objet | Oui |
| `amount` | Quantité | Non (1) |

**Exemple d'utilisation :**
```
/rcon give player:Steve item:minecraft:diamond_sword amount:1
```

---

### `/rcon gamemode`

Change le mode de jeu d'un joueur.

**Permission requise :** `ADMIN`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `player` | Joueur cible | Oui |
| `mode` | Mode de jeu | Oui |

**Modes disponibles :**
- `survival`
- `creative`
- `adventure`
- `spectator`

**Exemple d'utilisation :**
```
/rcon gamemode player:Steve mode:creative
```

---

### `/rcon time`

Modifie l'heure du monde.

**Permission requise :** `ADMIN`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `value` | Heure (day, night, noon, etc.) | Oui |

**Exemple d'utilisation :**
```
/rcon time value:day
```

---

### `/rcon weather`

Modifie la météo.

**Permission requise :** `ADMIN`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `type` | Type de météo | Oui |

**Types disponibles :**
- `clear`
- `rain`
- `thunder`

**Exemple d'utilisation :**
```
/rcon weather type:clear
```

---

## Commandes Notifications

### `/notifications configure`

Configure les notifications du bot.

**Permission requise :** `ADMIN`

**Utilisation interactive :**
La commande ouvre un menu interactif pour configurer :
- Channels de destination
- Types de notifications actives
- Mentions (rôles/users)
- Cooldowns

**Exemple d'utilisation :**
```
/notifications configure
```

---

### `/notifications toggle`

Active/désactive un type de notification.

**Permission requise :** `ADMIN`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `type` | Type de notification | Oui |
| `enabled` | État | Oui |

**Types disponibles :**
- `player_join` - Connexion joueur
- `player_leave` - Déconnexion joueur
- `player_death` - Mort joueur
- `player_achievement` - Succès/Advancement
- `server_start` - Démarrage serveur
- `server_stop` - Arrêt serveur
- `server_crash` - Crash serveur
- `performance_alert` - Alertes performance
- `backup_complete` - Backup terminé

**Exemple d'utilisation :**
```
/notifications toggle type:player_death enabled:true
```

---

### `/notifications test`

Envoie une notification de test.

**Permission requise :** `ADMIN`

**Options :**
| Option | Description | Obligatoire |
|--------|-------------|-------------|
| `type` | Type de notification | Oui |

**Exemple d'utilisation :**
```
/notifications test type:player_join
```

---

## Commandes Monitoring

### `/monitoring stats`

Affiche les statistiques de performance.

**Permission requise :** `PLAYER`

**Options :**
| Option | Description | Défaut |
|--------|-------------|--------|
| `period` | Période | 24h |

**Exemple d'utilisation :**
```
/monitoring stats period:7d
```

---

### `/monitoring alerts`

Affiche les alertes récentes.

**Permission requise :** `MODERATOR`

**Exemple d'utilisation :**
```
/monitoring alerts
```

---

### `/monitoring report`

Génère un rapport de performance.

**Permission requise :** `ADMIN`

**Options :**
| Option | Description | Défaut |
|--------|-------------|--------|
| `period` | Période du rapport | 7d |
| `format` | Format | embed |

**Exemple d'utilisation :**
```
/monitoring report period:30d
```

---

## Commandes Administration

### `/admin sync`

Synchronise les commandes slash avec Discord.

**Permission requise :** `ADMIN`

**Exemple d'utilisation :**
```
/admin sync
```

---

### `/admin logs`

Affiche les logs récents du bot.

**Permission requise :** `ADMIN`

**Options :**
| Option | Description | Défaut |
|--------|-------------|--------|
| `lines` | Nombre de lignes | 50 |
| `level` | Niveau de log | all |

**Exemple d'utilisation :**
```
/admin logs lines:100 level:error
```

---

### `/admin reload`

Recharge la configuration du bot.

**Permission requise :** `ADMIN`

**Exemple d'utilisation :**
```
/admin reload
```

---

## Référence rapide

### Commandes par permission

#### PLAYER (Tous)
| Commande | Description |
|----------|-------------|
| `/server status` | Voir le statut |
| `/players list` | Liste des joueurs |
| `/players info` | Info joueur |
| `/players whitelist list` | Voir la whitelist |
| `/monitoring stats` | Stats performance |

#### MODERATOR
| Commande | Description |
|----------|-------------|
| `/players kick` | Expulser un joueur |
| `/players whitelist add/remove` | Gérer la whitelist |
| `/rcon say` | Message serveur |
| `/rcon tp` | Téléporter |
| `/monitoring alerts` | Voir les alertes |

#### ADMIN
| Commande | Description |
|----------|-------------|
| `/server start/stop/restart` | Contrôle serveur |
| `/server backup` | Sauvegardes |
| `/server console` | Console directe |
| `/players ban/unban` | Bannissements |
| `/rcon execute` | Commandes RCON |
| `/notifications configure` | Config notifications |
| `/admin *` | Administration |

---

## Liens connexes

- [Système de permissions](permissions.md)
- [Commandes RCON](rcon.md)
- [Notifications](notifications.md)
