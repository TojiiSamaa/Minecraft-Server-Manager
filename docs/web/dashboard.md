# Dashboard Web

Guide complet du dashboard web pour la gestion du serveur Minecraft.

---

## Table des matieres

- [Vue d'ensemble](#vue-densemble)
- [Connexion OAuth Discord](#connexion-oauth-discord)
- [Interface principale](#interface-principale)
- [Gestion du serveur](#gestion-du-serveur)
- [Console et logs](#console-et-logs)
- [Gestion des joueurs](#gestion-des-joueurs)
- [Backups](#backups)
- [Parametres](#parametres)
- [API REST](#api-rest)

---

## Vue d'ensemble

Le dashboard web est une interface Next.js permettant de gerer votre serveur Minecraft depuis un navigateur.

### Fonctionnalites principales

- **Authentification** via Discord OAuth2
- **Monitoring** en temps reel du serveur
- **Console** interactive avec historique
- **Gestion** des joueurs, bans et whitelist
- **Backups** manuels et automatiques
- **Logs** consultables et exportables
- **API REST** pour integrations externes

### Acces

```
URL par defaut : http://localhost:3000
Production : https://votre-domaine.fr
```

---

## Connexion OAuth Discord

### Premiere connexion

1. Accedez au dashboard : `http://localhost:3000`
2. Cliquez sur **"Se connecter avec Discord"**
3. Autorisez l'application sur Discord
4. Vous etes redirige vers le dashboard

### Flux d'authentification

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Dashboard  │────▶│   Discord   │────▶│  Dashboard  │
│   Login     │     │    OAuth    │     │   Home      │
└─────────────┘     └─────────────┘     └─────────────┘
      │                    │                    │
      │  1. Redirection    │  2. Autorisation   │
      │                    │                    │
      └────────────────────┴────────────────────┘
                           │
                    3. Token + User Info
```

### Permissions requises

L'application Discord demande :
- `identify` - Votre nom d'utilisateur et avatar
- `guilds` - Liste de vos serveurs
- `guilds.members.read` - Vos roles sur le serveur

> **Note :** Vos informations Discord ne sont jamais partagees avec des tiers.

### Deconnexion

1. Cliquez sur votre avatar en haut a droite
2. Selectionnez **"Deconnexion"**
3. Votre session est supprimee

### Sessions

| Parametre | Valeur par defaut |
|-----------|-------------------|
| Duree de session | 7 jours |
| Renouvellement automatique | Oui |
| Sessions simultanees | Illimitees |

---

## Interface principale

### Layout general

```
┌─────────────────────────────────────────────────────────────┐
│  Logo    Navigation                        User ▼           │
├─────────┬───────────────────────────────────────────────────┤
│         │                                                   │
│  Menu   │              Contenu principal                    │
│         │                                                   │
│ Dashboard│  ┌─────────────────┐  ┌─────────────────┐       │
│ Serveur │  │  Status Card    │  │  Players Card   │       │
│ Joueurs │  └─────────────────┘  └─────────────────┘       │
│ Console │                                                   │
│ Backups │  ┌─────────────────┐  ┌─────────────────┐       │
│ Logs    │  │  Performance    │  │  Quick Actions  │       │
│ Settings│  └─────────────────┘  └─────────────────┘       │
│         │                                                   │
└─────────┴───────────────────────────────────────────────────┘
```

### Page d'accueil (Dashboard)

La page d'accueil affiche un resume de l'etat du serveur :

**Cartes d'information :**

1. **Statut serveur**
   - En ligne / Hors ligne
   - Version Minecraft
   - Uptime

2. **Joueurs**
   - Nombre connectes
   - Liste des joueurs
   - Graphique d'activite

3. **Performance**
   - TPS actuel
   - Utilisation RAM
   - Utilisation CPU

4. **Actions rapides**
   - Demarrer/Arreter
   - Redemarrer
   - Backup rapide

### Theme sombre/clair

Cliquez sur l'icone de theme dans la barre de navigation pour basculer.

```
Raccourci clavier : Ctrl + Shift + D
```

---

## Gestion du serveur

### Page Serveur

Acces : Menu > **Serveur**

### Controles principaux

```
┌─────────────────────────────────────────────────────────────┐
│  Controle du serveur                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Demarrer]  [Arreter]  [Redemarrer]  [Backup]             │
│                                                             │
│  Options d'arret :                                          │
│  ┌─────────────────────────────────────────┐               │
│  │ Delai : [60] secondes                   │               │
│  │ Raison : [________________________]     │               │
│  │ Notifier les joueurs : [x]              │               │
│  └─────────────────────────────────────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Informations serveur

| Information | Description |
|-------------|-------------|
| Version | 1.20.4 (NeoForge) |
| Adresse | play.monserveur.fr:25565 |
| Uptime | 3j 14h 25m |
| Derniere sauvegarde | Il y a 2 heures |

### Statistiques en temps reel

Le graphique affiche les 24 dernieres heures :

- **TPS** (Ticks par seconde)
- **RAM** (Utilisation memoire)
- **CPU** (Utilisation processeur)
- **Joueurs** (Nombre connectes)

### Configuration du serveur

Modifiez les parametres du serveur directement :

```
┌─────────────────────────────────────────────────────────────┐
│  Configuration                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  MOTD          : [Bienvenue sur MonServeur!        ]       │
│  Max joueurs   : [20        ]                              │
│  Mode de jeu   : [Survival ▼]                              │
│  Difficulte    : [Normal   ▼]                              │
│  PvP           : [x] Active                                │
│  Whitelist     : [ ] Active                                │
│                                                             │
│  [Sauvegarder]  [Reinitialiser]                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

> **Note :** Certaines modifications necessitent un redemarrage du serveur.

---

## Console et logs

### Console interactive

Acces : Menu > **Console**

```
┌─────────────────────────────────────────────────────────────┐
│  Console Minecraft                            [Effacer]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [14:32:15] [Server] Steve joined the game                 │
│  [14:32:20] [Server] <Steve> Hello everyone!               │
│  [14:33:01] [Server] Alex joined the game                  │
│  [14:33:15] [Server] <Alex> Hi Steve!                      │
│  [14:35:42] [Server] Steve has made the advancement        │
│            [Diamonds!]                                      │
│  [14:36:00] [RCON] list                                    │
│  [14:36:00] [Server] There are 2 of 20 players online:     │
│            Steve, Alex                                      │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  > [Entrez une commande...]                    [Envoyer]   │
└─────────────────────────────────────────────────────────────┘
```

### Commandes disponibles

Tapez des commandes Minecraft directement :

```
list                    # Liste des joueurs
say Hello!              # Message a tous
give Steve diamond 64   # Donner des objets
tp Steve Alex           # Teleporter
time set day            # Changer l'heure
weather clear           # Changer la meteo
```

### Filtres de logs

```
┌─────────────────────────────────────────────────────────────┐
│  Filtres                                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Niveau : [Tous ▼]  [INFO] [WARN] [ERROR]                  │
│                                                             │
│  Recherche : [_________________________]                    │
│                                                             │
│  Periode : [Aujourd'hui ▼]                                 │
│                                                             │
│  [Appliquer]  [Exporter CSV]                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Auto-scroll

L'auto-scroll est active par defaut. Desactivez-le en cliquant sur le bouton de pause.

---

## Gestion des joueurs

### Liste des joueurs

Acces : Menu > **Joueurs**

```
┌─────────────────────────────────────────────────────────────┐
│  Joueurs en ligne (5/20)                    [Rechercher]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Skin] Steve        En ligne depuis 2h 15m      [Actions]│
│  [Skin] Alex         En ligne depuis 45m         [Actions]│
│  [Skin] Notch        En ligne depuis 1h 30m      [Actions]│
│  [Skin] Herobrine    En ligne depuis 3h 10m      [Actions]│
│  [Skin] Jeb          En ligne depuis 20m         [Actions]│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Actions joueur

Cliquez sur **[Actions]** pour :

- **Kick** - Expulser le joueur
- **Ban** - Bannir le joueur
- **TP** - Teleporter le joueur
- **Give** - Donner des objets
- **Message** - Envoyer un message prive
- **Voir profil** - Statistiques detaillees

### Profil joueur

```
┌─────────────────────────────────────────────────────────────┐
│  Profil de Steve                                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────┐  UUID: a1b2c3d4-e5f6-7890-abcd-ef1234567890     │
│  │      │  Premiere connexion: 15/01/2024                  │
│  │ Skin │  Derniere connexion: En ligne maintenant         │
│  │      │  Temps de jeu total: 156h 32m                    │
│  └──────┘                                                   │
│                                                             │
│  Statistiques                                               │
│  ──────────────────────────────────────────                │
│  Morts: 42          Kills: 128                             │
│  Blocs casses: 15,432    Blocs places: 12,876             │
│  Distance parcourue: 234.5 km                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Whitelist

```
┌─────────────────────────────────────────────────────────────┐
│  Whitelist                           [Activer] [Ajouter]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Steve         Ajoute le 15/01/2024         [Retirer]      │
│  Alex          Ajoute le 10/01/2024         [Retirer]      │
│  Notch         Ajoute le 01/01/2024         [Retirer]      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Bans

```
┌─────────────────────────────────────────────────────────────┐
│  Joueurs bannis                              [Ajouter]     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Griefer       Grief - 15/01/2024           [Unban]        │
│  Hacker        Cheats - 10/01/2024          [Unban]        │
│                Expire le 17/01/2024                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Backups

### Page Backups

Acces : Menu > **Backups**

```
┌─────────────────────────────────────────────────────────────┐
│  Sauvegardes                                [Nouveau]      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  15/01/2024 14:00  │ Full     │ 2.3 GB │ [Restaurer] [DL] │
│  15/01/2024 08:00  │ Full     │ 2.2 GB │ [Restaurer] [DL] │
│  14/01/2024 20:00  │ Full     │ 2.1 GB │ [Restaurer] [DL] │
│  14/01/2024 14:00  │ Worlds   │ 1.8 GB │ [Restaurer] [DL] │
│  14/01/2024 08:00  │ Full     │ 2.0 GB │ [Restaurer] [DL] │
│                                                             │
│  Espace utilise : 12.4 GB / 50 GB                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Creer un backup

```
┌─────────────────────────────────────────────────────────────┐
│  Nouvelle sauvegarde                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Type :                                                     │
│  (*) Full - Mondes + Configs + Base de donnees             │
│  ( ) Worlds - Mondes uniquement                            │
│  ( ) Database - Base de donnees uniquement                 │
│  ( ) Quick - Monde principal uniquement                    │
│                                                             │
│  [x] Compresser (recommande)                               │
│  [x] Notifier sur Discord                                  │
│                                                             │
│  [Creer la sauvegarde]                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Restaurer un backup

> **Attention :** La restauration ecrase les donnees actuelles !

1. Cliquez sur **[Restaurer]**
2. Confirmez l'operation
3. Le serveur sera arrete automatiquement
4. Les donnees seront restaurees
5. Le serveur redemarrera

### Configuration automatique

```
┌─────────────────────────────────────────────────────────────┐
│  Backups automatiques                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [x] Activer les backups automatiques                      │
│                                                             │
│  Intervalle : [6] heures                                   │
│  Retention  : [10] backups                                 │
│  Type       : [Full ▼]                                     │
│                                                             │
│  [x] Inclure la base de donnees                            │
│  [x] Compresser                                            │
│  [x] Notifier sur Discord                                  │
│                                                             │
│  [Sauvegarder]                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Parametres

### Page Parametres

Acces : Menu > **Parametres** ou Avatar > **Parametres**

### Onglets disponibles

1. **General**
   - Langue de l'interface
   - Theme (sombre/clair)
   - Fuseau horaire

2. **Notifications**
   - Notifications navigateur
   - Sons
   - Email (si configure)

3. **Securite**
   - Sessions actives
   - Deconnexion de tous les appareils
   - Logs de connexion

4. **API**
   - Cle API personnelle
   - Webhooks

### Cle API

```
┌─────────────────────────────────────────────────────────────┐
│  Cle API                                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Votre cle API :                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ your-api-key-will-appear-here-after-generation    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [Copier]  [Regenerer]                                     │
│                                                             │
│  ⚠️ Ne partagez jamais cette cle !                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## API REST

### Authentification

Utilisez votre cle API dans l'en-tete :

```http
Authorization: Bearer sk_live_abc123...
```

### Endpoints principaux

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/server/status` | Statut du serveur |
| POST | `/api/server/start` | Demarrer le serveur |
| POST | `/api/server/stop` | Arreter le serveur |
| POST | `/api/server/restart` | Redemarrer |
| GET | `/api/players` | Liste des joueurs |
| GET | `/api/players/:name` | Info joueur |
| POST | `/api/players/:name/kick` | Kick joueur |
| POST | `/api/players/:name/ban` | Ban joueur |
| POST | `/api/rcon` | Commande RCON |
| GET | `/api/backups` | Liste des backups |
| POST | `/api/backups` | Creer backup |

### Exemples

**Obtenir le statut :**

```bash
curl -X GET "https://votre-domaine.fr/api/server/status" \
  -H "Authorization: Bearer sk_live_abc123..."
```

**Reponse :**

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
- [Troubleshooting](../troubleshooting.md)
