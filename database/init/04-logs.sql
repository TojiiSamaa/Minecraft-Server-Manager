-- ============================================================================
-- 04-logs.sql - Table logs.bot_logs pour le systeme de logs du bot Discord
-- Compatible avec le LogManager Python (batch insert, recherche, statistiques)
-- ============================================================================

-- ============================================================================
-- SCHEMA LOGS
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS logs;

COMMENT ON SCHEMA logs IS 'Schema pour le systeme de logs du bot Discord';

-- ============================================================================
-- TABLE PRINCIPALE: logs.bot_logs
-- Colonnes: id, timestamp, level, module, message, extra_data (JSONB)
--           guild_id, user_id, channel_id (optionnels)
-- ============================================================================

CREATE TABLE IF NOT EXISTS logs.bot_logs (
    -- Identifiant unique
    id BIGSERIAL PRIMARY KEY,

    -- Timestamp de l'entree de log
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Niveau de log: DEBUG, INFO, WARNING, ERROR, CRITICAL
    level VARCHAR(10) NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),

    -- Module source du log
    module VARCHAR(100) NOT NULL,

    -- Message du log
    message TEXT NOT NULL,

    -- Donnees additionnelles (JSONB pour flexibilite)
    extra_data JSONB,

    -- Contexte Discord (optionnels)
    guild_id BIGINT,       -- ID du serveur Discord
    user_id BIGINT,        -- ID de l'utilisateur Discord
    channel_id BIGINT      -- ID du channel Discord
);

-- Commentaires sur les colonnes
COMMENT ON TABLE logs.bot_logs IS 'Table principale des logs du bot Discord avec support JSONB';
COMMENT ON COLUMN logs.bot_logs.id IS 'Identifiant unique auto-incremente';
COMMENT ON COLUMN logs.bot_logs.timestamp IS 'Date et heure de l''entree de log (timezone-aware)';
COMMENT ON COLUMN logs.bot_logs.level IS 'Niveau de log: DEBUG(10), INFO(20), WARNING(30), ERROR(40), CRITICAL(50)';
COMMENT ON COLUMN logs.bot_logs.module IS 'Module source du log (ex: discord, minecraft, rcon, docker)';
COMMENT ON COLUMN logs.bot_logs.message IS 'Message du log';
COMMENT ON COLUMN logs.bot_logs.extra_data IS 'Donnees additionnelles en JSONB (exception, contexte, etc.)';
COMMENT ON COLUMN logs.bot_logs.guild_id IS 'ID du serveur Discord (snowflake, optionnel)';
COMMENT ON COLUMN logs.bot_logs.user_id IS 'ID de l''utilisateur Discord (snowflake, optionnel)';
COMMENT ON COLUMN logs.bot_logs.channel_id IS 'ID du channel Discord (snowflake, optionnel)';

-- ============================================================================
-- INDEX POUR OPTIMISER LES RECHERCHES
-- ============================================================================

-- Index principal sur timestamp (recherches par date, tri chronologique)
CREATE INDEX IF NOT EXISTS idx_bot_logs_timestamp
    ON logs.bot_logs (timestamp DESC);

-- Index sur le niveau de log (filtrage par niveau)
CREATE INDEX IF NOT EXISTS idx_bot_logs_level
    ON logs.bot_logs (level);

-- Index sur le module (filtrage par source)
CREATE INDEX IF NOT EXISTS idx_bot_logs_module
    ON logs.bot_logs (module);

-- Index composite pour les recherches frequentes (level + timestamp)
CREATE INDEX IF NOT EXISTS idx_bot_logs_level_timestamp
    ON logs.bot_logs (level, timestamp DESC);

-- Index composite pour les recherches par module et timestamp
CREATE INDEX IF NOT EXISTS idx_bot_logs_module_timestamp
    ON logs.bot_logs (module, timestamp DESC);

-- Index partiel sur guild_id (seulement si non null)
CREATE INDEX IF NOT EXISTS idx_bot_logs_guild_id
    ON logs.bot_logs (guild_id)
    WHERE guild_id IS NOT NULL;

-- Index partiel sur user_id (seulement si non null)
CREATE INDEX IF NOT EXISTS idx_bot_logs_user_id
    ON logs.bot_logs (user_id)
    WHERE user_id IS NOT NULL;

-- Index partiel sur channel_id (seulement si non null)
CREATE INDEX IF NOT EXISTS idx_bot_logs_channel_id
    ON logs.bot_logs (channel_id)
    WHERE channel_id IS NOT NULL;

-- Index GIN pour recherche dans extra_data JSONB
CREATE INDEX IF NOT EXISTS idx_bot_logs_extra_data_gin
    ON logs.bot_logs USING GIN (extra_data);

-- Index pour recherche full-text dans le message
CREATE INDEX IF NOT EXISTS idx_bot_logs_message_trgm
    ON logs.bot_logs USING GIN (message gin_trgm_ops);

-- ============================================================================
-- FONCTION: logs.insert_log
-- Insere une nouvelle entree de log
-- ============================================================================

CREATE OR REPLACE FUNCTION logs.insert_log(
    p_level VARCHAR(10),
    p_module VARCHAR(100),
    p_message TEXT,
    p_extra_data JSONB DEFAULT NULL,
    p_guild_id BIGINT DEFAULT NULL,
    p_user_id BIGINT DEFAULT NULL,
    p_channel_id BIGINT DEFAULT NULL
) RETURNS BIGINT AS $$
DECLARE
    new_id BIGINT;
BEGIN
    INSERT INTO logs.bot_logs (timestamp, level, module, message, extra_data, guild_id, user_id, channel_id)
    VALUES (NOW(), p_level, p_module, p_message, p_extra_data, p_guild_id, p_user_id, p_channel_id)
    RETURNING id INTO new_id;

    RETURN new_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION logs.insert_log IS 'Insere une nouvelle entree de log et retourne l''ID';

-- ============================================================================
-- FONCTIONS RACCOURCIES PAR NIVEAU
-- ============================================================================

CREATE OR REPLACE FUNCTION logs.debug(
    p_module VARCHAR(100),
    p_message TEXT,
    p_extra_data JSONB DEFAULT NULL
) RETURNS BIGINT AS $$
BEGIN
    RETURN logs.insert_log('DEBUG', p_module, p_message, p_extra_data);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION logs.info(
    p_module VARCHAR(100),
    p_message TEXT,
    p_extra_data JSONB DEFAULT NULL
) RETURNS BIGINT AS $$
BEGIN
    RETURN logs.insert_log('INFO', p_module, p_message, p_extra_data);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION logs.warning(
    p_module VARCHAR(100),
    p_message TEXT,
    p_extra_data JSONB DEFAULT NULL
) RETURNS BIGINT AS $$
BEGIN
    RETURN logs.insert_log('WARNING', p_module, p_message, p_extra_data);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION logs.error(
    p_module VARCHAR(100),
    p_message TEXT,
    p_extra_data JSONB DEFAULT NULL
) RETURNS BIGINT AS $$
BEGIN
    RETURN logs.insert_log('ERROR', p_module, p_message, p_extra_data);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION logs.critical(
    p_module VARCHAR(100),
    p_message TEXT,
    p_extra_data JSONB DEFAULT NULL
) RETURNS BIGINT AS $$
BEGIN
    RETURN logs.insert_log('CRITICAL', p_module, p_message, p_extra_data);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION logs.debug IS 'Raccourci pour log niveau DEBUG';
COMMENT ON FUNCTION logs.info IS 'Raccourci pour log niveau INFO';
COMMENT ON FUNCTION logs.warning IS 'Raccourci pour log niveau WARNING';
COMMENT ON FUNCTION logs.error IS 'Raccourci pour log niveau ERROR';
COMMENT ON FUNCTION logs.critical IS 'Raccourci pour log niveau CRITICAL';

-- ============================================================================
-- FONCTION: logs.search_logs
-- Recherche de logs avec filtres multiples
-- ============================================================================

CREATE OR REPLACE FUNCTION logs.search_logs(
    p_level VARCHAR(10) DEFAULT NULL,
    p_module VARCHAR(100) DEFAULT NULL,
    p_start_date TIMESTAMPTZ DEFAULT NULL,
    p_end_date TIMESTAMPTZ DEFAULT NULL,
    p_keyword TEXT DEFAULT NULL,
    p_guild_id BIGINT DEFAULT NULL,
    p_user_id BIGINT DEFAULT NULL,
    p_limit INTEGER DEFAULT 100,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    id BIGINT,
    timestamp TIMESTAMPTZ,
    level VARCHAR(10),
    module VARCHAR(100),
    message TEXT,
    extra_data JSONB,
    guild_id BIGINT,
    user_id BIGINT,
    channel_id BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        l.id,
        l.timestamp,
        l.level,
        l.module,
        l.message,
        l.extra_data,
        l.guild_id,
        l.user_id,
        l.channel_id
    FROM logs.bot_logs l
    WHERE (p_level IS NULL OR l.level = p_level)
    AND (p_module IS NULL OR l.module = p_module)
    AND (p_start_date IS NULL OR l.timestamp >= p_start_date)
    AND (p_end_date IS NULL OR l.timestamp <= p_end_date)
    AND (p_keyword IS NULL OR l.message ILIKE '%' || p_keyword || '%')
    AND (p_guild_id IS NULL OR l.guild_id = p_guild_id)
    AND (p_user_id IS NULL OR l.user_id = p_user_id)
    ORDER BY l.timestamp DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION logs.search_logs IS 'Recherche de logs avec filtres multiples et pagination';

-- ============================================================================
-- FONCTION: logs.count_logs
-- Compte les logs selon les filtres
-- ============================================================================

CREATE OR REPLACE FUNCTION logs.count_logs(
    p_level VARCHAR(10) DEFAULT NULL,
    p_module VARCHAR(100) DEFAULT NULL,
    p_start_date TIMESTAMPTZ DEFAULT NULL,
    p_end_date TIMESTAMPTZ DEFAULT NULL,
    p_keyword TEXT DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_count BIGINT;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM logs.bot_logs l
    WHERE (p_level IS NULL OR l.level = p_level)
    AND (p_module IS NULL OR l.module = p_module)
    AND (p_start_date IS NULL OR l.timestamp >= p_start_date)
    AND (p_end_date IS NULL OR l.timestamp <= p_end_date)
    AND (p_keyword IS NULL OR l.message ILIKE '%' || p_keyword || '%');

    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION logs.count_logs IS 'Compte le nombre de logs selon les filtres';

-- ============================================================================
-- FONCTION: logs.get_stats
-- Statistiques des logs sur une periode
-- ============================================================================

CREATE OR REPLACE FUNCTION logs.get_stats(
    p_period VARCHAR(10) DEFAULT 'day'  -- 'day', 'week', 'month'
)
RETURNS TABLE (
    period VARCHAR(10),
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    total_count BIGINT,
    debug_count BIGINT,
    info_count BIGINT,
    warning_count BIGINT,
    error_count BIGINT,
    critical_count BIGINT,
    top_modules JSONB,
    frequent_errors JSONB
) AS $$
DECLARE
    v_start_date TIMESTAMPTZ;
    v_end_date TIMESTAMPTZ;
BEGIN
    v_end_date := NOW();

    CASE p_period
        WHEN 'day' THEN v_start_date := v_end_date - INTERVAL '1 day';
        WHEN 'week' THEN v_start_date := v_end_date - INTERVAL '1 week';
        WHEN 'month' THEN v_start_date := v_end_date - INTERVAL '1 month';
        ELSE v_start_date := v_end_date - INTERVAL '1 day';
    END CASE;

    RETURN QUERY
    SELECT
        p_period,
        v_start_date,
        v_end_date,
        COUNT(*)::BIGINT,
        COUNT(*) FILTER (WHERE l.level = 'DEBUG')::BIGINT,
        COUNT(*) FILTER (WHERE l.level = 'INFO')::BIGINT,
        COUNT(*) FILTER (WHERE l.level = 'WARNING')::BIGINT,
        COUNT(*) FILTER (WHERE l.level = 'ERROR')::BIGINT,
        COUNT(*) FILTER (WHERE l.level = 'CRITICAL')::BIGINT,
        (
            SELECT COALESCE(jsonb_agg(jsonb_build_object('module', sub.module, 'count', sub.cnt)), '[]'::JSONB)
            FROM (
                SELECT l2.module, COUNT(*) as cnt
                FROM logs.bot_logs l2
                WHERE l2.timestamp >= v_start_date AND l2.timestamp <= v_end_date
                GROUP BY l2.module
                ORDER BY cnt DESC
                LIMIT 10
            ) sub
        ),
        (
            SELECT COALESCE(jsonb_agg(jsonb_build_object('message', sub.msg, 'count', sub.cnt)), '[]'::JSONB)
            FROM (
                SELECT LEFT(l3.message, 100) as msg, COUNT(*) as cnt
                FROM logs.bot_logs l3
                WHERE l3.timestamp >= v_start_date AND l3.timestamp <= v_end_date
                AND l3.level IN ('ERROR', 'CRITICAL')
                GROUP BY LEFT(l3.message, 100)
                ORDER BY cnt DESC
                LIMIT 10
            ) sub
        )
    FROM logs.bot_logs l
    WHERE l.timestamp >= v_start_date AND l.timestamp <= v_end_date;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION logs.get_stats IS 'Retourne les statistiques des logs sur une periode (day, week, month)';

-- ============================================================================
-- FONCTION: logs.cleanup_old_logs
-- Supprime les logs plus anciens que N jours
-- ============================================================================

CREATE OR REPLACE FUNCTION logs.cleanup_old_logs(
    p_retention_days INTEGER DEFAULT 90
)
RETURNS BIGINT AS $$
DECLARE
    v_deleted BIGINT;
    v_cutoff_date TIMESTAMPTZ;
BEGIN
    v_cutoff_date := NOW() - (p_retention_days || ' days')::INTERVAL;

    DELETE FROM logs.bot_logs
    WHERE timestamp < v_cutoff_date;

    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    -- Logger cette action
    PERFORM logs.info('log_manager', 'Cleanup des vieux logs effectue',
        jsonb_build_object(
            'retention_days', p_retention_days,
            'cutoff_date', v_cutoff_date,
            'deleted_count', v_deleted
        )
    );

    RETURN v_deleted;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION logs.cleanup_old_logs IS 'Supprime les logs plus anciens que N jours (defaut: 90)';

-- ============================================================================
-- FONCTION: logs.get_recent_errors
-- Recupere les erreurs recentes
-- ============================================================================

CREATE OR REPLACE FUNCTION logs.get_recent_errors(
    p_hours INTEGER DEFAULT 24,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    id BIGINT,
    timestamp TIMESTAMPTZ,
    level VARCHAR(10),
    module VARCHAR(100),
    message TEXT,
    extra_data JSONB,
    guild_id BIGINT,
    user_id BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        l.id,
        l.timestamp,
        l.level,
        l.module,
        l.message,
        l.extra_data,
        l.guild_id,
        l.user_id
    FROM logs.bot_logs l
    WHERE l.level IN ('ERROR', 'CRITICAL')
    AND l.timestamp >= NOW() - (p_hours || ' hours')::INTERVAL
    ORDER BY l.timestamp DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION logs.get_recent_errors IS 'Recupere les erreurs des dernieres N heures';

-- ============================================================================
-- VUE: logs.recent_errors
-- Vue pour les erreurs des dernieres 24 heures
-- ============================================================================

CREATE OR REPLACE VIEW logs.recent_errors AS
SELECT
    id,
    timestamp,
    level,
    module,
    message,
    extra_data,
    guild_id,
    user_id,
    channel_id
FROM logs.bot_logs
WHERE level IN ('ERROR', 'CRITICAL')
AND timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

COMMENT ON VIEW logs.recent_errors IS 'Erreurs et critiques des dernieres 24 heures';

-- ============================================================================
-- VUE: logs.today
-- Vue pour les logs d'aujourd'hui
-- ============================================================================

CREATE OR REPLACE VIEW logs.today AS
SELECT
    id,
    timestamp,
    level,
    module,
    message,
    extra_data,
    guild_id,
    user_id,
    channel_id
FROM logs.bot_logs
WHERE timestamp::DATE = CURRENT_DATE
ORDER BY timestamp DESC;

COMMENT ON VIEW logs.today IS 'Tous les logs d''aujourd''hui';

-- ============================================================================
-- VUE: logs.stats_by_level
-- Vue materialisee pour stats par niveau (rafraichir periodiquement)
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS logs.stats_by_level AS
SELECT
    date_trunc('hour', timestamp) as hour,
    level,
    COUNT(*) as count
FROM logs.bot_logs
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY date_trunc('hour', timestamp), level
ORDER BY hour DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_by_level_unique
    ON logs.stats_by_level (hour, level);

COMMENT ON MATERIALIZED VIEW logs.stats_by_level IS 'Statistiques par niveau et par heure (7 derniers jours)';

-- ============================================================================
-- VUE: logs.stats_by_module
-- Vue materialisee pour stats par module
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS logs.stats_by_module AS
SELECT
    date_trunc('hour', timestamp) as hour,
    module,
    COUNT(*) as count
FROM logs.bot_logs
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY date_trunc('hour', timestamp), module
ORDER BY hour DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_by_module_unique
    ON logs.stats_by_module (hour, module);

COMMENT ON MATERIALIZED VIEW logs.stats_by_module IS 'Statistiques par module et par heure (7 derniers jours)';

-- ============================================================================
-- FONCTION: logs.refresh_stats
-- Rafraichit les vues materialisees
-- ============================================================================

CREATE OR REPLACE FUNCTION logs.refresh_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY logs.stats_by_level;
    REFRESH MATERIALIZED VIEW CONCURRENTLY logs.stats_by_module;

    PERFORM logs.debug('log_manager', 'Vues materialisees rafraichies');
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION logs.refresh_stats IS 'Rafraichit les vues materialisees de statistiques';

-- ============================================================================
-- TABLE: logs.daily_summary
-- Statistiques journalieres pre-calculees
-- ============================================================================

CREATE TABLE IF NOT EXISTS logs.daily_summary (
    date DATE PRIMARY KEY,
    total_count INTEGER DEFAULT 0,
    debug_count INTEGER DEFAULT 0,
    info_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    critical_count INTEGER DEFAULT 0,
    by_module JSONB DEFAULT '{}',
    top_errors JSONB DEFAULT '[]',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE logs.daily_summary IS 'Resume journalier des logs';

-- Index sur la date
CREATE INDEX IF NOT EXISTS idx_daily_summary_date
    ON logs.daily_summary (date DESC);

-- ============================================================================
-- FONCTION: logs.update_daily_summary
-- Met a jour le resume journalier
-- ============================================================================

CREATE OR REPLACE FUNCTION logs.update_daily_summary(
    p_date DATE DEFAULT CURRENT_DATE
)
RETURNS void AS $$
DECLARE
    v_total INTEGER;
    v_debug INTEGER;
    v_info INTEGER;
    v_warning INTEGER;
    v_error INTEGER;
    v_critical INTEGER;
    v_by_module JSONB;
    v_top_errors JSONB;
BEGIN
    -- Compter par niveau
    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE level = 'DEBUG'),
        COUNT(*) FILTER (WHERE level = 'INFO'),
        COUNT(*) FILTER (WHERE level = 'WARNING'),
        COUNT(*) FILTER (WHERE level = 'ERROR'),
        COUNT(*) FILTER (WHERE level = 'CRITICAL')
    INTO v_total, v_debug, v_info, v_warning, v_error, v_critical
    FROM logs.bot_logs
    WHERE timestamp::DATE = p_date;

    -- Par module
    SELECT COALESCE(jsonb_object_agg(module, cnt), '{}'::JSONB) INTO v_by_module
    FROM (
        SELECT module, COUNT(*) as cnt
        FROM logs.bot_logs
        WHERE timestamp::DATE = p_date
        GROUP BY module
    ) sub;

    -- Top erreurs
    SELECT COALESCE(jsonb_agg(jsonb_build_object(
        'message', LEFT(message, 100),
        'module', module,
        'count', cnt
    ) ORDER BY cnt DESC), '[]'::JSONB) INTO v_top_errors
    FROM (
        SELECT LEFT(message, 100) as message, module, COUNT(*) as cnt
        FROM logs.bot_logs
        WHERE timestamp::DATE = p_date
        AND level IN ('ERROR', 'CRITICAL')
        GROUP BY LEFT(message, 100), module
        ORDER BY cnt DESC
        LIMIT 10
    ) sub;

    -- Upsert
    INSERT INTO logs.daily_summary (
        date, total_count, debug_count, info_count, warning_count,
        error_count, critical_count, by_module, top_errors, updated_at
    ) VALUES (
        p_date, v_total, v_debug, v_info, v_warning,
        v_error, v_critical, v_by_module, v_top_errors, NOW()
    )
    ON CONFLICT (date) DO UPDATE SET
        total_count = EXCLUDED.total_count,
        debug_count = EXCLUDED.debug_count,
        info_count = EXCLUDED.info_count,
        warning_count = EXCLUDED.warning_count,
        error_count = EXCLUDED.error_count,
        critical_count = EXCLUDED.critical_count,
        by_module = EXCLUDED.by_module,
        top_errors = EXCLUDED.top_errors,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION logs.update_daily_summary IS 'Met a jour le resume journalier (appeler via cron)';

-- ============================================================================
-- FONCTION: logs.maintenance
-- Maintenance complete des logs
-- ============================================================================

CREATE OR REPLACE FUNCTION logs.maintenance(
    p_retention_days INTEGER DEFAULT 90
)
RETURNS TABLE (
    action TEXT,
    result TEXT
) AS $$
DECLARE
    v_deleted BIGINT;
BEGIN
    -- Mettre a jour le resume d'hier
    PERFORM logs.update_daily_summary(CURRENT_DATE - 1);
    RETURN QUERY SELECT 'update_summary'::TEXT, 'Resume d''hier mis a jour';

    -- Rafraichir les vues materialisees
    PERFORM logs.refresh_stats();
    RETURN QUERY SELECT 'refresh_stats'::TEXT, 'Vues materialisees rafraichies';

    -- Nettoyer les vieux logs
    v_deleted := logs.cleanup_old_logs(p_retention_days);
    RETURN QUERY SELECT 'cleanup'::TEXT, format('%s logs supprimes', v_deleted);

    -- VACUUM de la table (optionnel, peut etre fait separement)
    -- VACUUM ANALYZE logs.bot_logs;

    RETURN QUERY SELECT 'maintenance'::TEXT, 'Complete';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION logs.maintenance IS 'Execute la maintenance complete des logs';

-- ============================================================================
-- EXTENSION POUR RECHERCHE FULL-TEXT (si pas deja installee)
-- ============================================================================

-- Active l'extension pg_trgm pour la recherche par trigrammes
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- GRANTS (ajuster selon les utilisateurs)
-- ============================================================================

-- Exemple de grants (a adapter selon votre configuration)
-- GRANT USAGE ON SCHEMA logs TO bot_user;
-- GRANT SELECT, INSERT ON logs.bot_logs TO bot_user;
-- GRANT SELECT ON logs.recent_errors, logs.today TO bot_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA logs TO bot_user;

-- ============================================================================
-- FIN DU FICHIER 04-logs.sql
-- ============================================================================
