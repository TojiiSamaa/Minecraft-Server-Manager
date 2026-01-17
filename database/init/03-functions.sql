-- ============================================================================
-- 03-functions.sql - Fonctions et Triggers PostgreSQL
-- ============================================================================

-- ============================================================================
-- TRIGGER: update_updated_at
-- Met à jour automatiquement le champ updated_at lors des modifications
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_updated_at_column() IS 'Met à jour automatiquement updated_at sur modification';

-- Application du trigger sur toutes les tables avec updated_at
DO $$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT table_schema, table_name
        FROM information_schema.columns
        WHERE column_name = 'updated_at'
        AND table_schema IN ('public', 'minecraft', 'discord', 'web', 'logs')
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS trigger_update_updated_at ON %I.%I;
            CREATE TRIGGER trigger_update_updated_at
                BEFORE UPDATE ON %I.%I
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        ', t.table_schema, t.table_name, t.table_schema, t.table_name);
    END LOOP;
END;
$$;

-- ============================================================================
-- FONCTION: calculate_session_duration
-- Calcule la durée d'une session et met à jour le temps de jeu du joueur
-- ============================================================================

CREATE OR REPLACE FUNCTION calculate_session_duration(
    p_session_id UUID,
    p_quit_time TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE (
    session_id UUID,
    duration_seconds INTEGER,
    player_uuid UUID,
    total_playtime_seconds BIGINT
) AS $$
DECLARE
    v_session RECORD;
    v_duration INTEGER;
    v_player_uuid UUID;
    v_total_playtime BIGINT;
BEGIN
    -- Récupérer la session
    SELECT s.id, s.player_id, s.player_uuid, s.join_time, s.is_active
    INTO v_session
    FROM minecraft.sessions s
    WHERE s.id = p_session_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Session non trouvée: %', p_session_id;
    END IF;

    IF NOT v_session.is_active THEN
        RAISE EXCEPTION 'La session est déjà terminée: %', p_session_id;
    END IF;

    -- Calculer la durée en secondes
    v_duration := EXTRACT(EPOCH FROM (p_quit_time - v_session.join_time))::INTEGER;
    v_player_uuid := v_session.player_uuid;

    -- Mettre à jour la session
    UPDATE minecraft.sessions
    SET quit_time = p_quit_time,
        duration_seconds = v_duration,
        is_active = FALSE
    WHERE id = p_session_id;

    -- Mettre à jour le temps de jeu total du joueur
    UPDATE minecraft.players
    SET playtime_seconds = playtime_seconds + v_duration,
        last_quit = p_quit_time,
        is_online = FALSE
    WHERE uuid = v_player_uuid
    RETURNING playtime_seconds INTO v_total_playtime;

    -- Retourner les résultats
    RETURN QUERY SELECT p_session_id, v_duration, v_player_uuid, v_total_playtime;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_session_duration IS 'Termine une session et met à jour le temps de jeu du joueur';

-- ============================================================================
-- FONCTION: get_player_stats
-- Récupère les statistiques complètes d'un joueur
-- ============================================================================

CREATE OR REPLACE FUNCTION get_player_stats(
    p_player_uuid UUID,
    p_period_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    player_uuid UUID,
    username VARCHAR(16),
    total_playtime_seconds BIGINT,
    playtime_period_seconds BIGINT,
    session_count INTEGER,
    session_count_period INTEGER,
    avg_session_duration_seconds INTEGER,
    first_join TIMESTAMPTZ,
    last_join TIMESTAMPTZ,
    days_since_last_join INTEGER,
    is_online BOOLEAN,
    current_session_duration_seconds INTEGER,
    stats JSONB
) AS $$
DECLARE
    v_player RECORD;
    v_period_start TIMESTAMPTZ;
    v_playtime_period BIGINT;
    v_session_count INTEGER;
    v_session_count_period INTEGER;
    v_avg_duration INTEGER;
    v_current_session_duration INTEGER;
BEGIN
    v_period_start := NOW() - (p_period_days || ' days')::INTERVAL;

    -- Récupérer les infos du joueur
    SELECT p.uuid, p.username, p.playtime_seconds, p.first_join,
           p.last_join, p.is_online, p.stats
    INTO v_player
    FROM minecraft.players p
    WHERE p.uuid = p_player_uuid;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Joueur non trouvé: %', p_player_uuid;
    END IF;

    -- Compter les sessions totales
    SELECT COUNT(*)::INTEGER
    INTO v_session_count
    FROM minecraft.sessions s
    WHERE s.player_uuid = p_player_uuid;

    -- Compter les sessions sur la période
    SELECT COUNT(*)::INTEGER
    INTO v_session_count_period
    FROM minecraft.sessions s
    WHERE s.player_uuid = p_player_uuid
    AND s.join_time >= v_period_start;

    -- Calculer le temps de jeu sur la période
    SELECT COALESCE(SUM(s.duration_seconds), 0)::BIGINT
    INTO v_playtime_period
    FROM minecraft.sessions s
    WHERE s.player_uuid = p_player_uuid
    AND s.join_time >= v_period_start
    AND s.duration_seconds IS NOT NULL;

    -- Calculer la durée moyenne des sessions
    SELECT COALESCE(AVG(s.duration_seconds), 0)::INTEGER
    INTO v_avg_duration
    FROM minecraft.sessions s
    WHERE s.player_uuid = p_player_uuid
    AND s.duration_seconds IS NOT NULL;

    -- Calculer la durée de la session actuelle si en ligne
    IF v_player.is_online THEN
        SELECT EXTRACT(EPOCH FROM (NOW() - s.join_time))::INTEGER
        INTO v_current_session_duration
        FROM minecraft.sessions s
        WHERE s.player_uuid = p_player_uuid
        AND s.is_active = TRUE
        ORDER BY s.join_time DESC
        LIMIT 1;
    ELSE
        v_current_session_duration := NULL;
    END IF;

    -- Retourner les statistiques
    RETURN QUERY SELECT
        v_player.uuid,
        v_player.username,
        v_player.playtime_seconds,
        v_playtime_period,
        v_session_count,
        v_session_count_period,
        v_avg_duration,
        v_player.first_join,
        v_player.last_join,
        EXTRACT(DAY FROM (NOW() - v_player.last_join))::INTEGER,
        v_player.is_online,
        v_current_session_duration,
        v_player.stats;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_player_stats IS 'Récupère les statistiques complètes d''un joueur sur une période donnée';

-- ============================================================================
-- FONCTION: log_audit_event
-- Enregistre un événement d'audit
-- ============================================================================

CREATE OR REPLACE FUNCTION log_audit_event(
    p_action audit_action,
    p_actor_id UUID DEFAULT NULL,
    p_actor_type VARCHAR(32) DEFAULT 'user',
    p_actor_identifier TEXT DEFAULT NULL,
    p_target_type VARCHAR(64) DEFAULT NULL,
    p_target_id TEXT DEFAULT NULL,
    p_target_identifier TEXT DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_old_value JSONB DEFAULT NULL,
    p_new_value JSONB DEFAULT NULL,
    p_severity log_severity DEFAULT 'info',
    p_ip_address INET DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'::JSONB
)
RETURNS UUID AS $$
DECLARE
    v_audit_id UUID;
    v_request_id UUID;
BEGIN
    -- Générer un request_id unique pour traçabilité
    v_request_id := uuid_generate_v4();

    -- Insérer l'événement d'audit
    INSERT INTO logs.audit (
        action,
        severity,
        actor_id,
        actor_type,
        actor_identifier,
        target_type,
        target_id,
        target_identifier,
        description,
        old_value,
        new_value,
        ip_address,
        user_agent,
        request_id,
        metadata
    ) VALUES (
        p_action,
        p_severity,
        p_actor_id,
        p_actor_type,
        p_actor_identifier,
        p_target_type,
        p_target_id,
        p_target_identifier,
        p_description,
        p_old_value,
        p_new_value,
        p_ip_address,
        p_user_agent,
        v_request_id,
        p_metadata
    )
    RETURNING id INTO v_audit_id;

    RETURN v_audit_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION log_audit_event IS 'Enregistre un événement dans le journal d''audit';

-- Fonction simplifiée pour les cas courants
CREATE OR REPLACE FUNCTION log_audit_simple(
    p_action audit_action,
    p_actor_id UUID,
    p_description TEXT,
    p_target_type VARCHAR(64) DEFAULT NULL,
    p_target_id TEXT DEFAULT NULL
)
RETURNS UUID AS $$
BEGIN
    RETURN log_audit_event(
        p_action := p_action,
        p_actor_id := p_actor_id,
        p_description := p_description,
        p_target_type := p_target_type,
        p_target_id := p_target_id
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION log_audit_simple IS 'Version simplifiée de log_audit_event pour les cas courants';

-- ============================================================================
-- FONCTION: cleanup_expired_data
-- Nettoie les données expirées (sessions, logs, sauvegardes)
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_expired_data(
    p_session_retention_days INTEGER DEFAULT 90,
    p_server_stats_retention_days INTEGER DEFAULT 30,
    p_server_events_retention_days INTEGER DEFAULT 90,
    p_audit_retention_days INTEGER DEFAULT 365,
    p_dry_run BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
    table_name TEXT,
    rows_deleted BIGINT,
    space_freed_estimate TEXT
) AS $$
DECLARE
    v_web_sessions_deleted BIGINT := 0;
    v_mc_sessions_deleted BIGINT := 0;
    v_server_stats_deleted BIGINT := 0;
    v_server_events_deleted BIGINT := 0;
    v_audit_deleted BIGINT := 0;
    v_backups_deleted BIGINT := 0;
BEGIN
    -- Nettoyer les sessions web expirées
    IF p_dry_run THEN
        SELECT COUNT(*) INTO v_web_sessions_deleted
        FROM web.sessions
        WHERE status = 'expired'
           OR expires_at < NOW()
           OR created_at < NOW() - (p_session_retention_days || ' days')::INTERVAL;
    ELSE
        WITH deleted AS (
            DELETE FROM web.sessions
            WHERE status = 'expired'
               OR expires_at < NOW()
               OR created_at < NOW() - (p_session_retention_days || ' days')::INTERVAL
            RETURNING *
        )
        SELECT COUNT(*) INTO v_web_sessions_deleted FROM deleted;
    END IF;

    RETURN QUERY SELECT 'web.sessions'::TEXT, v_web_sessions_deleted,
        pg_size_pretty(v_web_sessions_deleted * 200); -- Estimation ~200 bytes/row

    -- Nettoyer les anciennes sessions Minecraft (garder les sessions terminées)
    IF p_dry_run THEN
        SELECT COUNT(*) INTO v_mc_sessions_deleted
        FROM minecraft.sessions
        WHERE is_active = FALSE
        AND created_at < NOW() - (p_session_retention_days || ' days')::INTERVAL;
    ELSE
        WITH deleted AS (
            DELETE FROM minecraft.sessions
            WHERE is_active = FALSE
            AND created_at < NOW() - (p_session_retention_days || ' days')::INTERVAL
            RETURNING *
        )
        SELECT COUNT(*) INTO v_mc_sessions_deleted FROM deleted;
    END IF;

    RETURN QUERY SELECT 'minecraft.sessions'::TEXT, v_mc_sessions_deleted,
        pg_size_pretty(v_mc_sessions_deleted * 150);

    -- Nettoyer les anciennes statistiques serveur
    IF p_dry_run THEN
        SELECT COUNT(*) INTO v_server_stats_deleted
        FROM minecraft.server_stats
        WHERE recorded_at < NOW() - (p_server_stats_retention_days || ' days')::INTERVAL;
    ELSE
        WITH deleted AS (
            DELETE FROM minecraft.server_stats
            WHERE recorded_at < NOW() - (p_server_stats_retention_days || ' days')::INTERVAL
            RETURNING *
        )
        SELECT COUNT(*) INTO v_server_stats_deleted FROM deleted;
    END IF;

    RETURN QUERY SELECT 'minecraft.server_stats'::TEXT, v_server_stats_deleted,
        pg_size_pretty(v_server_stats_deleted * 300);

    -- Nettoyer les anciens événements serveur
    IF p_dry_run THEN
        SELECT COUNT(*) INTO v_server_events_deleted
        FROM logs.server_events
        WHERE created_at < NOW() - (p_server_events_retention_days || ' days')::INTERVAL;
    ELSE
        WITH deleted AS (
            DELETE FROM logs.server_events
            WHERE created_at < NOW() - (p_server_events_retention_days || ' days')::INTERVAL
            RETURNING *
        )
        SELECT COUNT(*) INTO v_server_events_deleted FROM deleted;
    END IF;

    RETURN QUERY SELECT 'logs.server_events'::TEXT, v_server_events_deleted,
        pg_size_pretty(v_server_events_deleted * 400);

    -- Nettoyer les anciens logs d'audit (conserver plus longtemps)
    IF p_dry_run THEN
        SELECT COUNT(*) INTO v_audit_deleted
        FROM logs.audit
        WHERE created_at < NOW() - (p_audit_retention_days || ' days')::INTERVAL
        AND severity NOT IN ('error', 'critical'); -- Garder les erreurs critiques
    ELSE
        WITH deleted AS (
            DELETE FROM logs.audit
            WHERE created_at < NOW() - (p_audit_retention_days || ' days')::INTERVAL
            AND severity NOT IN ('error', 'critical')
            RETURNING *
        )
        SELECT COUNT(*) INTO v_audit_deleted FROM deleted;
    END IF;

    RETURN QUERY SELECT 'logs.audit'::TEXT, v_audit_deleted,
        pg_size_pretty(v_audit_deleted * 500);

    -- Nettoyer les sauvegardes expirées (marquer comme deleted)
    IF p_dry_run THEN
        SELECT COUNT(*) INTO v_backups_deleted
        FROM minecraft.backups
        WHERE expires_at IS NOT NULL
        AND expires_at < NOW()
        AND status != 'deleted';
    ELSE
        WITH updated AS (
            UPDATE minecraft.backups
            SET status = 'deleted',
                updated_at = NOW()
            WHERE expires_at IS NOT NULL
            AND expires_at < NOW()
            AND status != 'deleted'
            RETURNING *
        )
        SELECT COUNT(*) INTO v_backups_deleted FROM updated;
    END IF;

    RETURN QUERY SELECT 'minecraft.backups (marked)'::TEXT, v_backups_deleted,
        'N/A - files need manual cleanup'::TEXT;

    -- Log de l'opération de nettoyage si pas en dry_run
    IF NOT p_dry_run THEN
        PERFORM log_audit_event(
            p_action := 'command_execute',
            p_actor_type := 'system',
            p_description := 'Nettoyage automatique des données expirées',
            p_metadata := jsonb_build_object(
                'web_sessions_deleted', v_web_sessions_deleted,
                'mc_sessions_deleted', v_mc_sessions_deleted,
                'server_stats_deleted', v_server_stats_deleted,
                'server_events_deleted', v_server_events_deleted,
                'audit_deleted', v_audit_deleted,
                'backups_marked', v_backups_deleted,
                'dry_run', p_dry_run
            )
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_data IS 'Nettoie les données expirées avec rétention configurable. Utiliser dry_run=TRUE pour prévisualiser.';

-- ============================================================================
-- FONCTION: log_server_event
-- Enregistre un événement serveur Minecraft
-- ============================================================================

CREATE OR REPLACE FUNCTION log_server_event(
    p_event_type server_event_type,
    p_message TEXT DEFAULT NULL,
    p_player_uuid UUID DEFAULT NULL,
    p_player_name VARCHAR(16) DEFAULT NULL,
    p_severity log_severity DEFAULT 'info',
    p_details JSONB DEFAULT '{}'::JSONB,
    p_world_name VARCHAR(64) DEFAULT NULL,
    p_location JSONB DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_event_id UUID;
    v_current_tps NUMERIC(5, 2);
    v_current_memory NUMERIC(5, 2);
BEGIN
    -- Récupérer les stats actuelles du serveur
    SELECT tps, memory_percent
    INTO v_current_tps, v_current_memory
    FROM minecraft.server_stats
    WHERE status = 'online'
    ORDER BY recorded_at DESC
    LIMIT 1;

    -- Insérer l'événement
    INSERT INTO logs.server_events (
        event_type,
        severity,
        player_uuid,
        player_name,
        message,
        details,
        world_name,
        location,
        server_tps,
        server_memory_percent
    ) VALUES (
        p_event_type,
        p_severity,
        p_player_uuid,
        p_player_name,
        p_message,
        p_details,
        p_world_name,
        p_location,
        v_current_tps,
        v_current_memory
    )
    RETURNING id INTO v_event_id;

    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION log_server_event IS 'Enregistre un événement serveur avec contexte TPS/RAM automatique';

-- ============================================================================
-- FONCTION: get_server_stats_summary
-- Récupère un résumé des statistiques serveur sur une période
-- ============================================================================

CREATE OR REPLACE FUNCTION get_server_stats_summary(
    p_period_hours INTEGER DEFAULT 24
)
RETURNS TABLE (
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    avg_tps NUMERIC(5, 2),
    min_tps NUMERIC(5, 2),
    max_tps NUMERIC(5, 2),
    avg_memory_percent NUMERIC(5, 2),
    max_memory_percent NUMERIC(5, 2),
    avg_cpu_percent NUMERIC(5, 2),
    max_cpu_percent NUMERIC(5, 2),
    avg_players INTEGER,
    max_players INTEGER,
    total_uptime_seconds BIGINT,
    sample_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        NOW() - (p_period_hours || ' hours')::INTERVAL AS period_start,
        NOW() AS period_end,
        ROUND(AVG(s.tps), 2) AS avg_tps,
        MIN(s.tps) AS min_tps,
        MAX(s.tps) AS max_tps,
        ROUND(AVG(s.memory_percent), 2) AS avg_memory_percent,
        MAX(s.memory_percent) AS max_memory_percent,
        ROUND(AVG(s.cpu_percent), 2) AS avg_cpu_percent,
        MAX(s.cpu_percent) AS max_cpu_percent,
        ROUND(AVG(s.players_online))::INTEGER AS avg_players,
        MAX(s.players_online) AS max_players,
        COALESCE(MAX(s.uptime_seconds), 0) AS total_uptime_seconds,
        COUNT(*) AS sample_count
    FROM minecraft.server_stats s
    WHERE s.recorded_at >= NOW() - (p_period_hours || ' hours')::INTERVAL
    AND s.status = 'online';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_server_stats_summary IS 'Résumé des performances serveur sur une période en heures';

-- ============================================================================
-- FONCTION: start_player_session
-- Démarre une nouvelle session pour un joueur
-- ============================================================================

CREATE OR REPLACE FUNCTION start_player_session(
    p_player_uuid UUID,
    p_ip_address INET DEFAULT NULL,
    p_client_version VARCHAR(32) DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_player_id UUID;
    v_session_id UUID;
BEGIN
    -- Vérifier que le joueur existe
    SELECT id INTO v_player_id
    FROM minecraft.players
    WHERE uuid = p_player_uuid;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Joueur non trouvé: %', p_player_uuid;
    END IF;

    -- Fermer les sessions actives existantes (au cas où)
    UPDATE minecraft.sessions
    SET is_active = FALSE,
        quit_time = NOW(),
        duration_seconds = EXTRACT(EPOCH FROM (NOW() - join_time))::INTEGER
    WHERE player_uuid = p_player_uuid
    AND is_active = TRUE;

    -- Créer la nouvelle session
    INSERT INTO minecraft.sessions (
        player_id,
        player_uuid,
        ip_address,
        client_version
    ) VALUES (
        v_player_id,
        p_player_uuid,
        p_ip_address,
        p_client_version
    )
    RETURNING id INTO v_session_id;

    -- Mettre à jour le joueur
    UPDATE minecraft.players
    SET is_online = TRUE,
        last_join = NOW()
    WHERE uuid = p_player_uuid;

    -- Logger l'événement
    PERFORM log_server_event(
        p_event_type := 'player_join',
        p_player_uuid := p_player_uuid,
        p_message := 'Joueur connecté',
        p_details := jsonb_build_object(
            'session_id', v_session_id,
            'client_version', p_client_version
        )
    );

    RETURN v_session_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION start_player_session IS 'Démarre une session de jeu pour un joueur';

-- ============================================================================
-- FONCTION: end_player_session
-- Termine la session active d'un joueur
-- ============================================================================

CREATE OR REPLACE FUNCTION end_player_session(
    p_player_uuid UUID
)
RETURNS TABLE (
    session_id UUID,
    duration_seconds INTEGER,
    total_playtime_seconds BIGINT
) AS $$
DECLARE
    v_session_id UUID;
    v_result RECORD;
BEGIN
    -- Trouver la session active
    SELECT id INTO v_session_id
    FROM minecraft.sessions
    WHERE player_uuid = p_player_uuid
    AND is_active = TRUE
    ORDER BY join_time DESC
    LIMIT 1;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Aucune session active pour le joueur: %', p_player_uuid;
    END IF;

    -- Utiliser calculate_session_duration pour terminer la session
    SELECT * INTO v_result
    FROM calculate_session_duration(v_session_id);

    -- Logger l'événement
    PERFORM log_server_event(
        p_event_type := 'player_quit',
        p_player_uuid := p_player_uuid,
        p_message := 'Joueur déconnecté',
        p_details := jsonb_build_object(
            'session_id', v_session_id,
            'duration_seconds', v_result.duration_seconds
        )
    );

    RETURN QUERY SELECT v_result.session_id, v_result.duration_seconds, v_result.total_playtime_seconds;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION end_player_session IS 'Termine la session de jeu active d''un joueur';

-- ============================================================================
-- INDEX ADDITIONNELS POUR LES PERFORMANCES
-- ============================================================================

-- Index composite pour les recherches fréquentes
CREATE INDEX IF NOT EXISTS idx_sessions_player_active
    ON minecraft.sessions(player_uuid, is_active)
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_audit_actor_action
    ON logs.audit(actor_id, action, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_server_events_player_type
    ON logs.server_events(player_uuid, event_type, created_at DESC)
    WHERE player_uuid IS NOT NULL;

-- Index pour les statistiques temporelles
CREATE INDEX IF NOT EXISTS idx_server_stats_hourly
    ON minecraft.server_stats(DATE_TRUNC('hour', recorded_at), status);

-- Index BRIN pour les tables volumineuses (logs) - efficace pour données ordonnées
CREATE INDEX IF NOT EXISTS idx_audit_created_brin
    ON logs.audit USING BRIN(created_at);

CREATE INDEX IF NOT EXISTS idx_server_events_created_brin
    ON logs.server_events USING BRIN(created_at);

CREATE INDEX IF NOT EXISTS idx_server_stats_recorded_brin
    ON minecraft.server_stats USING BRIN(recorded_at);

-- ============================================================================
-- FIN DES FONCTIONS ET TRIGGERS
-- ============================================================================
