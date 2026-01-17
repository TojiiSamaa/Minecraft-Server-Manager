# Dashboard Web

Guide complet du dashboard web pour la gestion du serveur Minecraft.

---

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Connexion OAuth Discord](#connexion-oauth-discord)
- [Interface principale](#interface-principale)
- [Gestion du serveur](#gestion-du-serveur)
- [Console et logs](#console-et-logs)
- [Gestion des joueurs](#gestion-des-joueurs)
- [Backups](#backups)
- [Paramètres](#paramètres)
- [API REST](#api-rest)

---

## Vue d'ensemble

Le dashboard web est une interface Next.js permettant de gérer votre serveur Minecraft depuis un navigateur.

### Fonctionnalités principales

- **Authentification** via Discord OAuth2
- **Monitoring** en temps réel du serveur
- **Console** interactive avec historique
- **Gestion** des joueurs, bans et whitelist
- **Backups** manuels et automatiques
- **Logs** consultables et exportables
- **API REST** pour intégrations externes

### Accès

```
URL par défaut : http://localhost:3000
Production : https://votre-domaine.fr
```

---

## Connexion OAuth Discord

### Première connexion

1. Accédez au dashboard : `http://localhost:3000`
2. Cliquez sur **"Se connecter avec Discord"**
3. Autorisez l'application sur Discord
4. Vous êtes redirigé vers le dashboard

### Flux d'authentification

```
+-------------+     +-------------+     +-------------+
|  Dashboard  |---->|   Discord   |---->|  Dashboard  |
|   Login     |     |    OAuth    |     |   Home      |
+-------------+     +-------------+     +-------------+
      |                    |                    |
      |  1. Redirection    |  2. Autorisation   |
      |                    |                    |
      +--------------------+--------------------+
                           |
                    3. Token + User Info
```

### Permissions requises

L'application Discord demande :
- `identify` - Votre nom d'utilisateur et avatar
- `guilds` - Liste de vos serveurs
- `guilds.members.read` - Vos rôles sur le serveur

> **Note :** Vos informations Discord ne sont jamais partagées avec des tiers.

### Déconnexion

1. Cliquez sur votre avatar en haut à droite
2. Sélectionnez **"Déconnexion"**
3. Votre session est supprimée

### Sessions

| Paramètre | Valeur par défaut |
|-----------|-------------------|
| Durée de session | 7 jours |
| Renouvellement automatique | Oui |
| Sessions simultanées | Illimitées |

---

## Interface principale

### Layout général

```
+-------------------------------------------------------------+
|  Logo    Navigation                        User v           |
+---------+---------------------------------------------------+
|         |                                                   |
|  Menu   |              Contenu principal                    |
|         |                                                   |
| Dashboard|  +-----------------+  +-----------------+        |
| Serveur |  |  Status Card    |  |  Players Card   |        |
| Joueurs |  +-----------------+  +-----------------+        |
| Console |                                                   |
| Backups |  +-----------------+  +-----------------+        |
| Logs    |  |  Performance    |  |  Quick Actions  |        |
| Settings|  +-----------------+  +-----------------+        |
|         |                                                   |
+---------+---------------------------------------------------+
```

### Page d'accueil (Dashboard)

La page d'accueil affiche un résumé de l'état du serveur :

**Cartes d'information :**

1. **Statut serveur**
   - En ligne / Hors ligne
   - Version Minecraft
   - Uptime

2. **Joueurs**
   - Nombre connectés
   - Liste des joueurs
   - Graphique d'activité

3. **Performance**
   - TPS actuel
   - Utilisation RAM
   - Utilisation CPU

4. **Actions rapides**
   - Démarrer/Arrêter
   - Redémarrer
   - Backup rapide

### Thème sombre/clair

Cliquez sur l'icône de thème dans la barre de navigation pour basculer.

```
Raccourci clavier : Ctrl + Shift + D
```

---

## Gestion du serveur

### Page Serveur

Accès : Menu > **Serveur**

### Contrôles principaux

```
+-------------------------------------------------------------+
|  Contrôle du serveur                                        |
+-------------------------------------------------------------+
|                                                             |
|  [Démarrer]  [Arrêter]  [Redémarrer]  [Backup]             |
|                                                             |
|  Options d'arrêt :                                          |
|  +-----------------------------------------+                |
|  | Délai : [60] secondes                   |                |
|  | Raison : [________________________]     |                |
|  | Notifier les joueurs : [x]              |                |
|  +-----------------------------------------+                |
|                                                             |
+-------------------------------------------------------------+
```

### Informations serveur

| Information | Description |
|-------------|-------------|
| Version | 1.20.4 (NeoForge) |
| Adresse | play.monserveur.fr:25565 |
| Uptime | 3j 14h 25m |
| Dernière sauvegarde | Il y a 2 heures |

### Statistiques en temps réel

Le graphique affiche les 24 dernières heures :

- **TPS** (Ticks par seconde)
- **RAM** (Utilisation mémoire)
- **CPU** (Utilisation processeur)
- **Joueurs** (Nombre connectés)

### Configuration du serveur

Modifiez les paramètres du serveur directement :

```
+-------------------------------------------------------------+
|  Configuration                                              |
+-------------------------------------------------------------+
|                                                             |
|  MOTD          : [Bienvenue sur MonServeur!        ]        |
|  Max joueurs   : [20        ]                               |
|  Mode de jeu   : [Survival v]                               |
|  Difficulté    : [Normal   v]                               |
|  PvP           : [x] Activé                                 |
|  Whitelist     : [ ] Activée                                |
|                                                             |
|  [Sauvegarder]  [Réinitialiser]                             |
|                                                             |
+-------------------------------------------------------------+
```

> **Note :** Certaines modifications nécessitent un redémarrage du serveur.

---

## Console et logs

### Console interactive

Accès : Menu > **Console**

```
+-------------------------------------------------------------+
|  Console Minecraft                            [Effacer]     |
+-------------------------------------------------------------+
|                                                             |
|  [14:32:15] [Server] Steve joined the game                  |
|  [14:32:20] [Server] <Steve> Hello everyone!                |
|  [14:33:01] [Server] Alex joined the game                   |
|  [14:33:15] [Server] <Alex> Hi Steve!                       |
|  [14:35:42] [Server] Steve has made the advancement         |
|            [Diamonds!]                                      |
|  [14:36:00] [RCON] list                                     |
|  [14:36:00] [Server] There are 2 of 20 players online:      |
|            Steve, Alex                                      |
|                                                             |
+-------------------------------------------------------------+
|  > [Entrez une commande...]                    [Envoyer]    |
+-------------------------------------------------------------+
```

### Commandes disponibles

Tapez des commandes Minecraft directement :

```
list                    # Liste des joueurs
say Hello!              # Message à tous
give Steve diamond 64   # Donner des objets
tp Steve Alex           # Téléporter
time set day            # Changer l'heure
weather clear           # Changer la météo
```

### Filtres de logs

```
+-------------------------------------------------------------+
|  Filtres                                                    |
+-------------------------------------------------------------+
|                                                             |
|  Niveau : [Tous v]  [INFO] [WARN] [ERROR]                   |
|                                                             |
|  Recherche : [_________________________]                    |
|                                                             |
|  Période : [Aujourd'hui v]                                  |
|                                                             |
|  [Appliquer]  [Exporter CSV]                                |
|                                                             |
+-------------------------------------------------------------+
```

### Auto-scroll

L'auto-scroll est activé par défaut. Désactivez-le en cliquant sur le bouton de pause.

---

## Gestion des joueurs

### Liste des joueurs

Accès : Menu > **Joueurs**

```
+-------------------------------------------------------------+
|  Joueurs en ligne (5/20)                    [Rechercher]    |
+-------------------------------------------------------------+
|                                                             |
|  [Skin] Steve        En ligne depuis 2h 15m      [Actions]  |
|  [Skin] Alex         En ligne depuis 45m         [Actions]  |
|  [Skin] Notch        En ligne depuis 1h 30m      [Actions]  |
|  [Skin] Herobrine    En ligne depuis 3h 10m      [Actions]  |
|  [Skin] Jeb          En ligne depuis 20m         [Actions]  |
|                                                             |
+-------------------------------------------------------------+
```

### Actions joueur

Cliquez sur **[Actions]** pour :

- **Kick** - Expulser le joueur
- **Ban** - Bannir le joueur
- **TP** - Téléporter le joueur
- **Give** - Donner des objets
- **Message** - Envoyer un message privé
- **Voir profil** - Statistiques détaillées

### Profil joueur

```
+-------------------------------------------------------------+
|  Profil de Steve                                            |
+-------------------------------------------------------------+
|                                                             |
|  +------+  UUID: a1b2c3d4-e5f6-7890-abcd-ef1234567890       |
|  |      |  Première connexion: 15/01/2024                   |
|  | Skin |  Dernière connexion: En ligne maintenant          |
|  |      |  Temps de jeu total: 156h 32m                     |
|  +------+                                                   |
|                                                             |
|  Statistiques                                               |
|  -----------------------------------------------------      |
|  Morts: 42          Kills: 128                              |
|  Blocs cassés: 15,432    Blocs placés: 12,876               |
|  Distance parcourue: 234.5 km                               |
|                                                             |
+-------------------------------------------------------------+
```

### Whitelist

```
+-------------------------------------------------------------+
|  Whitelist                           [Activer] [Ajouter]    |
+-------------------------------------------------------------+
|                                                             |
|  Steve         Ajouté le 15/01/2024         [Retirer]       |
|  Alex          Ajouté le 10/01/2024         [Retirer]       |
|  Notch         Ajouté le 01/01/2024         [Retirer]       |
|                                                             |
+-------------------------------------------------------------+
```

### Bans

```
+-------------------------------------------------------------+
|  Joueurs bannis                              [Ajouter]      |
+-------------------------------------------------------------+
|                                                             |
|  Griefer       Grief - 15/01/2024           [Unban]         |
|  Hacker        Cheats - 10/01/2024          [Unban]         |
|                Expire le 17/01/2024                         |
|                                                             |
+-------------------------------------------------------------+
```

---

## Backups

### Page Backups

Accès : Menu > **Backups**

```
+-------------------------------------------------------------+
|  Sauvegardes                                [Nouveau]       |
+-------------------------------------------------------------+
|                                                             |
|  15/01/2024 14:00  | Full     | 2.3 GB | [Restaurer] [DL]  |
|  15/01/2024 08:00  | Full     | 2.2 GB | [Restaurer] [DL]  |
|  14/01/2024 20:00  | Full     | 2.1 GB | [Restaurer] [DL]  |
|  14/01/2024 14:00  | Worlds   | 1.8 GB | [Restaurer] [DL]  |
|  14/01/2024 08:00  | Full     | 2.0 GB | [Restaurer] [DL]  |
|                                                             |
|  Espace utilisé : 12.4 GB / 50 GB                           |
|                                                             |
+-------------------------------------------------------------+
```

### Créer un backup

```
+-------------------------------------------------------------+
|  Nouvelle sauvegarde                                        |
+-------------------------------------------------------------+
|                                                             |
|  Type :                                                     |
|  (*) Full - Mondes + Configs + Base de données              |
|  ( ) Worlds - Mondes uniquement                             |
|  ( ) Database - Base de données uniquement                  |
|  ( ) Quick - Monde principal uniquement                     |
|                                                             |
|  [x] Compresser (recommandé)                                |
|  [x] Notifier sur Discord                                   |
|                                                             |
|  [Créer la sauvegarde]                                      |
|                                                             |
+-------------------------------------------------------------+
```

### Restaurer un backup

> **Attention :** La restauration écrase les données actuelles !

1. Cliquez sur **[Restaurer]**
2. Confirmez l'opération
3. Le serveur sera arrêté automatiquement
4. Les données seront restaurées
5. Le serveur redémarrera

### Configuration automatique

```
+-------------------------------------------------------------+
|  Backups automatiques                                       |
+-------------------------------------------------------------+
|                                                             |
|  [x] Activer les backups automatiques                       |
|                                                             |
|  Intervalle : [6] heures                                    |
|  Rétention  : [10] backups                                  |
|  Type       : [Full v]                                      |
|                                                             |
|  [x] Inclure la base de données                             |
|  [x] Compresser                                             |
|  [x] Notifier sur Discord                                   |
|                                                             |
|  [Sauvegarder]                                              |
|                                                             |
+-------------------------------------------------------------+
```

---

## Paramètres

### Page Paramètres

Accès : Menu > **Paramètres** ou Avatar > **Paramètres**

### Onglets disponibles

1. **Général**
   - Langue de l'interface
   - Thème (sombre/clair)
   - Fuseau horaire

2. **Notifications**
   - Notifications navigateur
   - Sons
   - Email (si configuré)

3. **Sécurité**
   - Sessions actives
   - Déconnexion de tous les appareils
   - Logs de connexion

4. **API**
   - Clé API personnelle
   - Webhooks

### Clé API

```
+-------------------------------------------------------------+
|  Clé API                                                    |
+-------------------------------------------------------------+
|                                                             |
|  Votre clé API :                                            |
|  +-----------------------------------------------------+    |
|  | your-api-key-will-appear-here-after-generation     |    |
|  +-----------------------------------------------------+    |
|                                                             |
|  [Copier]  [Régénérer]                                      |
|                                                             |
|  Ne partagez jamais cette clé !                             |
|                                                             |
+-------------------------------------------------------------+
```

---

## API REST

### Authentification

Utilisez votre clé API dans l'en-tête :

```http
Authorization: Bearer sk_live_abc123...
```

### Endpoints principaux

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/server/status` | Statut du serveur |
| POST | `/api/server/start` | Démarrer le serveur |
| POST | `/api/server/stop` | Arrêter le serveur |
| POST | `/api/server/restart` | Redémarrer |
| GET | `/api/players` | Liste des joueurs |
| GET | `/api/players/:name` | Info joueur |
| POST | `/api/players/:name/kick` | Kick joueur |
| POST | `/api/players/:name/ban` | Ban joueur |
| POST | `/api/rcon` | Commande RCON |
| GET | `/api/backups` | Liste des backups |
| POST | `/api/backups` | Créer backup |

### Exemples

**Obtenir le statut :**

```bash
curl -X GET "https://votre-domaine.fr/api/server/status" \
  -H "Authorization: Bearer sk_live_abc123..."
```

**Réponse :**

```json
{
  "status": "online",
  "version": "1.20.4",
  "players": {
    "online": 5,
    "max": 20,
    "list": ["Steve", "Alex", "Notch", "Herobrine", "Jeb"]
  },
  "performance": {
    "tps": 19.8,
    "ram": {
      "used": 2150,
      "max": 4096
    }
  },
  "uptime": 310500
}
```

**Envoyer une commande RCON :**

```bash
curl -X POST "https://votre-domaine.fr/api/rcon" \
  -H "Authorization: Bearer sk_live_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"command": "say Hello from the API!"}'
```

---

## Liens connexes

- [Configuration](../configuration.md)
- [Services Docker](../docker/services.md)
- [API REST](../api.md)
- [Dépannage](../troubleshooting.md)
