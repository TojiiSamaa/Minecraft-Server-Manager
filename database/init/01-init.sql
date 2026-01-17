-- ============================================================================
-- 01-init.sql - Initialisation de la base de données PostgreSQL
-- Extensions, Schémas et Types ENUM
-- ============================================================================

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

-- Extension pour la génération d'UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Extension pour les fonctions cryptographiques (hachage, chiffrement)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Extension pour les comparaisons de texte insensibles à la casse
CREATE EXTENSION IF NOT EXISTS "citext";

-- ============================================================================
-- SCHEMAS
-- ============================================================================

-- Schéma pour les données Minecraft (joueurs, sessions, stats serveur)
CREATE SCHEMA IF NOT EXISTS minecraft;
COMMENT ON SCHEMA minecraft IS 'Données relatives au serveur Minecraft';

-- Schéma pour les données Discord (guilds, configuration)
CREATE SCHEMA IF NOT EXISTS discord;
COMMENT ON SCHEMA discord IS 'Données relatives au bot Discord';

-- Schéma pour les données web (sessions web, tokens)
CREATE SCHEMA IF NOT EXISTS web;
COMMENT ON SCHEMA web IS 'Données relatives à l''interface web';

-- Schéma pour les logs et audit
CREATE SCHEMA IF NOT EXISTS logs;
COMMENT ON SCHEMA logs IS 'Logs d''audit et événements serveur';

-- ============================================================================
-- TYPES ENUM
-- ============================================================================

-- Rôles utilisateur dans le système
CREATE TYPE user_role AS ENUM (
    'guest',           -- Visiteur non enregistré
    'member',          -- Membre standard
    'vip',             -- Membre VIP
    'moderator',       -- Modérateur
    'admin',           -- Administrateur
    'owner'            -- Propriétaire du serveur
);
COMMENT ON TYPE user_role IS 'Niveaux de rôle des utilisateurs';

-- Statut du serveur Minecraft
CREATE TYPE server_status AS ENUM (
    'offline',         -- Serveur arrêté
    'starting',        -- Démarrage en cours
    'online',          -- En ligne et accessible
    'stopping',        -- Arrêt en cours
    'restarting',      -- Redémarrage en cours
    'maintenance',     -- Mode maintenance
    'crashed'          -- Crash détecté
);
COMMENT ON TYPE server_status IS 'États possibles du serveur Minecraft';

-- Statut d'une sauvegarde
CREATE TYPE backup_status AS ENUM (
    'pending',         -- En attente
    'in_progress',     -- En cours
    'completed',       -- Terminée avec succès
    'failed',          -- Échec
    'deleted'          -- Supprimée
);
COMMENT ON TYPE backup_status IS 'États possibles d''une sauvegarde';

-- Type de sauvegarde
CREATE TYPE backup_type AS ENUM (
    'full',            -- Sauvegarde complète
    'incremental',     -- Sauvegarde incrémentale
    'world_only',      -- Monde uniquement
    'config_only',     -- Configuration uniquement
    'manual'           -- Sauvegarde manuelle
);
COMMENT ON TYPE backup_type IS 'Types de sauvegardes disponibles';

-- Type de notification Discord
CREATE TYPE notification_type AS ENUM (
    'server_start',    -- Démarrage serveur
    'server_stop',     -- Arrêt serveur
    'player_join',     -- Connexion joueur
    'player_leave',    -- Déconnexion joueur
    'backup_complete', -- Sauvegarde terminée
    'backup_failed',   -- Échec sauvegarde
    'high_cpu',        -- CPU élevé
    'high_ram',        -- RAM élevée
    'low_tps',         -- TPS bas
    'player_death',    -- Mort d'un joueur
    'achievement',     -- Succès obtenu
    'chat_message',    -- Message chat (relay)
    'console_error',   -- Erreur console
    'whitelist_add',   -- Ajout whitelist
    'whitelist_remove' -- Retrait whitelist
);
COMMENT ON TYPE notification_type IS 'Types de notifications Discord';

-- Niveau de sévérité des logs
CREATE TYPE log_severity AS ENUM (
    'debug',           -- Debug
    'info',            -- Information
    'warning',         -- Avertissement
    'error',           -- Erreur
    'critical'         -- Critique
);
COMMENT ON TYPE log_severity IS 'Niveaux de sévérité des logs';

-- Type d'action d'audit
CREATE TYPE audit_action AS ENUM (
    'user_create',     -- Création utilisateur
    'user_update',     -- Modification utilisateur
    'user_delete',     -- Suppression utilisateur
    'role_change',     -- Changement de rôle
    'permission_grant',-- Attribution permission
    'permission_revoke',-- Retrait permission
    'server_start',    -- Démarrage serveur
    'server_stop',     -- Arrêt serveur
    'server_restart',  -- Redémarrage serveur
    'backup_create',   -- Création sauvegarde
    'backup_restore',  -- Restauration sauvegarde
    'backup_delete',   -- Suppression sauvegarde
    'config_update',   -- Modification configuration
    'whitelist_add',   -- Ajout whitelist
    'whitelist_remove',-- Retrait whitelist
    'ban_player',      -- Bannissement joueur
    'unban_player',    -- Débannissement joueur
    'kick_player',     -- Expulsion joueur
    'command_execute', -- Exécution commande
    'login_success',   -- Connexion réussie
    'login_failed',    -- Échec connexion
    'logout'           -- Déconnexion
);
COMMENT ON TYPE audit_action IS 'Types d''actions pour l''audit';

-- Type d'événement serveur Minecraft
CREATE TYPE server_event_type AS ENUM (
    'start',           -- Démarrage
    'stop',            -- Arrêt
    'crash',           -- Crash
    'player_join',     -- Connexion joueur
    'player_quit',     -- Déconnexion joueur
    'player_death',    -- Mort joueur
    'player_achievement',-- Succès joueur
    'chat',            -- Message chat
    'command',         -- Commande exécutée
    'world_save',      -- Sauvegarde monde
    'plugin_load',     -- Chargement plugin
    'plugin_unload',   -- Déchargement plugin
    'error',           -- Erreur
    'warning',         -- Avertissement
    'tps_drop',        -- Chute TPS
    'memory_warning'   -- Avertissement mémoire
);
COMMENT ON TYPE server_event_type IS 'Types d''événements serveur Minecraft';

-- Statut de session web
CREATE TYPE session_status AS ENUM (
    'active',          -- Session active
    'expired',         -- Session expirée
    'revoked'          -- Session révoquée manuellement
);
COMMENT ON TYPE session_status IS 'États possibles d''une session web';

-- ============================================================================
-- CONFIGURATION PAR DÉFAUT
-- ============================================================================

-- Définir le search_path par défaut pour inclure tous les schémas
ALTER DATABASE CURRENT_DATABASE() SET search_path TO public, minecraft, discord, web, logs;

-- ============================================================================
-- FIN DE L'INITIALISATION
-- ============================================================================
