-- ============================================================================
-- 02-tables.sql - Création des tables
-- Tables principales pour users, minecraft, discord et logs
-- ============================================================================

-- ============================================================================
-- TABLE: public.users (Table principale des utilisateurs)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    discord_id BIGINT UNIQUE,
    minecraft_uuid UUID UNIQUE,
    username CITEXT NOT NULL,
    email CITEXT UNIQUE,
    password_hash TEXT,
    role user_role NOT NULL DEFAULT 'member',
    permissions JSONB NOT NULL DEFAULT '[]'::JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT users_discord_or_minecraft CHECK (
        discord_id IS NOT NULL OR minecraft_uuid IS NOT NULL
    )
);

COMMENT ON TABLE public.users IS 'Utilisateurs du système (liés à Discord et/ou Minecraft)';
COMMENT ON COLUMN public.users.discord_id IS 'ID Discord (snowflake)';
COMMENT ON COLUMN public.users.minecraft_uuid IS 'UUID Minecraft du joueur';
COMMENT ON COLUMN public.users.permissions IS 'Permissions additionnelles en JSON';

-- Index pour la table users
CREATE INDEX IF NOT EXISTS idx_users_discord_id ON public.users(discord_id) WHERE discord_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_minecraft_uuid ON public.users(minecraft_uuid) WHERE minecraft_uuid IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON public.users(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_users_created_at ON public.users(created_at DESC);

-- ============================================================================
-- TABLE: minecraft.players (Joueurs Minecraft)
-- ============================================================================

CREATE TABLE IF NOT EXISTS minecraft.players (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    uuid UUID NOT NULL UNIQUE,
    username VARCHAR(16) NOT NULL,
    display_name VARCHAR(64),
    first_join TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_join TIMESTAMPTZ,
    last_quit TIMESTAMPTZ,
    playtime_seconds BIGINT NOT NULL DEFAULT 0,
    is_online BOOLEAN NOT NULL DEFAULT FALSE,
    is_whitelisted BOOLEAN NOT NULL DEFAULT FALSE,
    is_banned BOOLEAN NOT NULL DEFAULT FALSE,
    ban_reason TEXT,
    ban_expires_at TIMESTAMPTZ,
    stats JSONB NOT NULL DEFAULT '{}'::JSONB,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE minecraft.players IS 'Joueurs Minecraft enregistrés sur le serveur';
COMMENT ON COLUMN minecraft.players.uuid IS 'UUID Minecraft officiel';
COMMENT ON COLUMN minecraft.players.playtime_seconds IS 'Temps de jeu total en secondes';
COMMENT ON COLUMN minecraft.players.stats IS 'Statistiques du joueur (kills, deaths, blocks, etc.)';

-- Index pour la table players
CREATE INDEX IF NOT EXISTS idx_players_uuid ON minecraft.players(uuid);
CREATE INDEX IF NOT EXISTS idx_players_username ON minecraft.players(username);
CREATE INDEX IF NOT EXISTS idx_players_is_online ON minecraft.players(is_online) WHERE is_online = TRUE;
CREATE INDEX IF NOT EXISTS idx_players_is_whitelisted ON minecraft.players(is_whitelisted) WHERE is_whitelisted = TRUE;
CREATE INDEX IF NOT EXISTS idx_players_playtime ON minecraft.players(playtime_seconds DESC);
CREATE INDEX IF NOT EXISTS idx_players_last_join ON minecraft.players(last_join DESC);
CREATE INDEX IF NOT EXISTS idx_players_user_id ON minecraft.players(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_players_stats ON minecraft.players USING GIN(stats);

-- ============================================================================
-- TABLE: minecraft.sessions (Sessions de jeu)
-- ============================================================================

CREATE TABLE IF NOT EXISTS minecraft.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID NOT NULL REFERENCES minecraft.players(id) ON DELETE CASCADE,
    player_uuid UUID NOT NULL,
    join_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    quit_time TIMESTAMPTZ,
    duration_seconds INTEGER,
    ip_address INET,
    client_version VARCHAR(32),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE minecraft.sessions IS 'Sessions de connexion des joueurs';
COMMENT ON COLUMN minecraft.sessions.duration_seconds IS 'Durée calculée automatiquement à la déconnexion';

-- Index pour la table sessions
CREATE INDEX IF NOT EXISTS idx_sessions_player_id ON minecraft.sessions(player_id);
CREATE INDEX IF NOT EXISTS idx_sessions_player_uuid ON minecraft.sessions(player_uuid);
CREATE INDEX IF NOT EXISTS idx_sessions_join_time ON minecraft.sessions(join_time DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON minecraft.sessions(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_sessions_date ON minecraft.sessions(DATE(join_time));

-- ============================================================================
-- TABLE: minecraft.server_stats (Snapshots performance serveur)
-- ============================================================================

CREATE TABLE IF NOT EXISTS minecraft.server_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status server_status NOT NULL DEFAULT 'offline',
    tps NUMERIC(5, 2),
    tps_1m_avg NUMERIC(5, 2),
    tps_5m_avg NUMERIC(5, 2),
    tps_15m_avg NUMERIC(5, 2),
    memory_used_mb INTEGER,
    memory_max_mb INTEGER,
    memory_percent NUMERIC(5, 2),
    cpu_percent NUMERIC(5, 2),
    cpu_system_percent NUMERIC(5, 2),
    players_online INTEGER NOT NULL DEFAULT 0,
    players_max INTEGER,
    chunks_loaded INTEGER,
    entities_count INTEGER,
    world_size_mb BIGINT,
    uptime_seconds BIGINT,
    metadata JSONB DEFAULT '{}'::JSONB
);

COMMENT ON TABLE minecraft.server_stats IS 'Snapshots périodiques des performances serveur';
COMMENT ON COLUMN minecraft.server_stats.tps IS 'Ticks par seconde (20 = optimal)';

-- Index pour la table server_stats
CREATE INDEX IF NOT EXISTS idx_server_stats_recorded_at ON minecraft.server_stats(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_server_stats_status ON minecraft.server_stats(status);
CREATE INDEX IF NOT EXISTS idx_server_stats_tps ON minecraft.server_stats(tps) WHERE tps IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_server_stats_date ON minecraft.server_stats(DATE(recorded_at));

-- Partitionnement par mois (optionnel, commenté par défaut)
-- CREATE INDEX IF NOT EXISTS idx_server_stats_month ON minecraft.server_stats(DATE_TRUNC('month', recorded_at));

-- ============================================================================
-- TABLE: minecraft.backups (Sauvegardes)
-- ============================================================================

CREATE TABLE IF NOT EXISTS minecraft.backups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    backup_type backup_type NOT NULL DEFAULT 'full',
    status backup_status NOT NULL DEFAULT 'pending',
    file_path TEXT,
    file_size_bytes BIGINT,
    checksum VARCHAR(64),
    compression_type VARCHAR(16) DEFAULT 'gzip',
    worlds_included TEXT[],
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    error_message TEXT,
    initiated_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
    is_automatic BOOLEAN NOT NULL DEFAULT FALSE,
    retention_days INTEGER DEFAULT 30,
    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE minecraft.backups IS 'Sauvegardes du serveur Minecraft';
COMMENT ON COLUMN minecraft.backups.checksum IS 'SHA-256 du fichier de sauvegarde';
COMMENT ON COLUMN minecraft.backups.worlds_included IS 'Liste des mondes inclus dans la sauvegarde';

-- Index pour la table backups
CREATE INDEX IF NOT EXISTS idx_backups_status ON minecraft.backups(status);
CREATE INDEX IF NOT EXISTS idx_backups_type ON minecraft.backups(backup_type);
CREATE INDEX IF NOT EXISTS idx_backups_created_at ON minecraft.backups(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backups_expires_at ON minecraft.backups(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_backups_initiated_by ON minecraft.backups(initiated_by) WHERE initiated_by IS NOT NULL;

-- ============================================================================
-- TABLE: discord.guilds (Serveurs Discord)
-- ============================================================================

CREATE TABLE IF NOT EXISTS discord.guilds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guild_id BIGINT NOT NULL UNIQUE,
    guild_name VARCHAR(100) NOT NULL,
    owner_id BIGINT,
    prefix VARCHAR(10) DEFAULT '!',
    language VARCHAR(5) DEFAULT 'fr',
    timezone VARCHAR(64) DEFAULT 'Europe/Paris',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_premium BOOLEAN NOT NULL DEFAULT FALSE,
    premium_expires_at TIMESTAMPTZ,

    -- Channels configurés
    log_channel_id BIGINT,
    status_channel_id BIGINT,
    chat_channel_id BIGINT,
    console_channel_id BIGINT,
    admin_channel_id BIGINT,

    -- Rôles configurés
    admin_role_id BIGINT,
    moderator_role_id BIGINT,
    member_role_id BIGINT,
    linked_role_id BIGINT,

    -- Configuration
    settings JSONB NOT NULL DEFAULT '{}'::JSONB,
    features_enabled JSONB NOT NULL DEFAULT '[]'::JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE discord.guilds IS 'Configuration des serveurs Discord';
COMMENT ON COLUMN discord.guilds.guild_id IS 'ID Discord du serveur (snowflake)';
COMMENT ON COLUMN discord.guilds.settings IS 'Configuration personnalisée en JSON';
COMMENT ON COLUMN discord.guilds.features_enabled IS 'Liste des fonctionnalités activées';

-- Index pour la table guilds
CREATE INDEX IF NOT EXISTS idx_guilds_guild_id ON discord.guilds(guild_id);
CREATE INDEX IF NOT EXISTS idx_guilds_is_active ON discord.guilds(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_guilds_is_premium ON discord.guilds(is_premium) WHERE is_premium = TRUE;

-- ============================================================================
-- TABLE: discord.notification_config (Configuration des notifications)
-- ============================================================================

CREATE TABLE IF NOT EXISTS discord.notification_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guild_id UUID NOT NULL REFERENCES discord.guilds(id) ON DELETE CASCADE,
    notification_type notification_type NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    channel_id BIGINT,
    role_to_mention BIGINT,
    message_template TEXT,
    embed_color INTEGER,
    cooldown_seconds INTEGER DEFAULT 0,
    last_sent_at TIMESTAMPTZ,
    conditions JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_guild_notification UNIQUE(guild_id, notification_type)
);

COMMENT ON TABLE discord.notification_config IS 'Configuration des notifications par type et serveur';
COMMENT ON COLUMN discord.notification_config.conditions IS 'Conditions pour déclencher (ex: TPS < 15)';
COMMENT ON COLUMN discord.notification_config.cooldown_seconds IS 'Délai minimum entre deux notifications';

-- Index pour la table notification_config
CREATE INDEX IF NOT EXISTS idx_notification_config_guild_id ON discord.notification_config(guild_id);
CREATE INDEX IF NOT EXISTS idx_notification_config_type ON discord.notification_config(notification_type);
CREATE INDEX IF NOT EXISTS idx_notification_config_enabled ON discord.notification_config(is_enabled) WHERE is_enabled = TRUE;

-- ============================================================================
-- TABLE: web.sessions (Sessions web)
-- ============================================================================

CREATE TABLE IF NOT EXISTS web.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    status session_status NOT NULL DEFAULT 'active',
    ip_address INET,
    user_agent TEXT,
    device_info JSONB,
    expires_at TIMESTAMPTZ NOT NULL,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE web.sessions IS 'Sessions d''authentification web';
COMMENT ON COLUMN web.sessions.token_hash IS 'Hash SHA-256 du token de session';

-- Index pour la table web.sessions
CREATE INDEX IF NOT EXISTS idx_web_sessions_user_id ON web.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_web_sessions_token_hash ON web.sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_web_sessions_status ON web.sessions(status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_web_sessions_expires_at ON web.sessions(expires_at);

-- ============================================================================
-- TABLE: logs.audit (Logs d'audit)
-- ============================================================================

CREATE TABLE IF NOT EXISTS logs.audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action audit_action NOT NULL,
    severity log_severity NOT NULL DEFAULT 'info',
    actor_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    actor_type VARCHAR(32) DEFAULT 'user',
    actor_identifier TEXT,
    target_type VARCHAR(64),
    target_id TEXT,
    target_identifier TEXT,
    description TEXT,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    request_id UUID,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE logs.audit IS 'Journal d''audit des actions administratives';
COMMENT ON COLUMN logs.audit.actor_id IS 'Utilisateur ayant effectué l''action';
COMMENT ON COLUMN logs.audit.old_value IS 'Valeur avant modification';
COMMENT ON COLUMN logs.audit.new_value IS 'Valeur après modification';

-- Index pour la table audit
CREATE INDEX IF NOT EXISTS idx_audit_action ON logs.audit(action);
CREATE INDEX IF NOT EXISTS idx_audit_severity ON logs.audit(severity);
CREATE INDEX IF NOT EXISTS idx_audit_actor_id ON logs.audit(actor_id) WHERE actor_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_target ON logs.audit(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON logs.audit(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_date ON logs.audit(DATE(created_at));

-- Index pour recherche dans les métadonnées
CREATE INDEX IF NOT EXISTS idx_audit_metadata ON logs.audit USING GIN(metadata);

-- ============================================================================
-- TABLE: logs.server_events (Événements serveur Minecraft)
-- ============================================================================

CREATE TABLE IF NOT EXISTS logs.server_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type server_event_type NOT NULL,
    severity log_severity NOT NULL DEFAULT 'info',
    player_uuid UUID,
    player_name VARCHAR(16),
    message TEXT,
    details JSONB DEFAULT '{}'::JSONB,
    world_name VARCHAR(64),
    location JSONB,
    server_tps NUMERIC(5, 2),
    server_memory_percent NUMERIC(5, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE logs.server_events IS 'Événements du serveur Minecraft';
COMMENT ON COLUMN logs.server_events.location IS 'Coordonnées JSON {x, y, z, world}';
COMMENT ON COLUMN logs.server_events.details IS 'Détails additionnels de l''événement';

-- Index pour la table server_events
CREATE INDEX IF NOT EXISTS idx_server_events_type ON logs.server_events(event_type);
CREATE INDEX IF NOT EXISTS idx_server_events_severity ON logs.server_events(severity);
CREATE INDEX IF NOT EXISTS idx_server_events_player_uuid ON logs.server_events(player_uuid) WHERE player_uuid IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_server_events_created_at ON logs.server_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_server_events_date ON logs.server_events(DATE(created_at));

-- Index pour recherche full-text dans les messages
CREATE INDEX IF NOT EXISTS idx_server_events_message ON logs.server_events USING GIN(to_tsvector('french', COALESCE(message, '')));

-- Index GIN pour recherche dans les détails
CREATE INDEX IF NOT EXISTS idx_server_events_details ON logs.server_events USING GIN(details);

-- ============================================================================
-- FIN DE LA CRÉATION DES TABLES
-- ============================================================================
