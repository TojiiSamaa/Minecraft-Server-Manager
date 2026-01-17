-- ============================================
-- FICHIER: 05-security.sql
-- Description: Rôles, permissions et politiques de sécurité
-- ============================================

-- ============================================
-- SECTION 1: CRÉATION DES RÔLES APPLICATIFS
-- ============================================

-- Rôle en lecture seule (pour monitoring, analytics)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mc_readonly') THEN
        CREATE ROLE mc_readonly NOLOGIN;
    END IF;
END
$$;

-- Rôle lecture/écriture (pour le bot Discord)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mc_bot') THEN
        CREATE ROLE mc_bot NOLOGIN;
    END IF;
END
$$;

-- Rôle lecture/écriture (pour l'application web)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mc_web') THEN
        CREATE ROLE mc_web NOLOGIN;
    END IF;
END
$$;

-- Rôle administrateur (pour maintenance)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mc_admin') THEN
        CREATE ROLE mc_admin NOLOGIN;
    END IF;
END
$$;

-- ============================================
-- SECTION 2: RÉVOCATION DES ACCÈS PUBLICS
-- ============================================

-- Révoquer tous les accès publics sur les schemas
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA minecraft FROM PUBLIC;
REVOKE ALL ON SCHEMA discord FROM PUBLIC;
REVOKE ALL ON SCHEMA web FROM PUBLIC;
REVOKE ALL ON SCHEMA logs FROM PUBLIC;

-- ============================================
-- SECTION 3: PERMISSIONS mc_readonly
-- ============================================

-- Accès aux schemas
GRANT USAGE ON SCHEMA public, minecraft, discord, logs TO mc_readonly;

-- SELECT uniquement
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mc_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA minecraft TO mc_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA discord TO mc_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA logs TO mc_readonly;

-- Permissions par défaut pour les futures tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mc_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA minecraft GRANT SELECT ON TABLES TO mc_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA discord GRANT SELECT ON TABLES TO mc_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA logs GRANT SELECT ON TABLES TO mc_readonly;

-- ============================================
-- SECTION 4: PERMISSIONS mc_bot
-- ============================================

-- Accès aux schemas
GRANT USAGE ON SCHEMA public, minecraft, discord, logs TO mc_bot;

-- Lecture/Écriture sur tables principales
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA minecraft TO mc_bot;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA discord TO mc_bot;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA logs TO mc_bot;
GRANT SELECT, UPDATE ON public.users TO mc_bot;

-- Séquences
GRANT USAGE ON ALL SEQUENCES IN SCHEMA minecraft TO mc_bot;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA discord TO mc_bot;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA logs TO mc_bot;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mc_bot;

-- Fonctions
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA minecraft TO mc_bot;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA discord TO mc_bot;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA logs TO mc_bot;

-- PAS de DELETE pour le bot (sauf logs après 90 jours via fonction)
-- PAS d'accès au schema web

-- Permissions par défaut
ALTER DEFAULT PRIVILEGES IN SCHEMA minecraft GRANT SELECT, INSERT, UPDATE ON TABLES TO mc_bot;
ALTER DEFAULT PRIVILEGES IN SCHEMA discord GRANT SELECT, INSERT, UPDATE ON TABLES TO mc_bot;
ALTER DEFAULT PRIVILEGES IN SCHEMA logs GRANT SELECT, INSERT ON TABLES TO mc_bot;

-- ============================================
-- SECTION 5: PERMISSIONS mc_web
-- ============================================

-- Accès aux schemas
GRANT USAGE ON SCHEMA public, minecraft, discord, web TO mc_web;

-- Permissions sur le schema web
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA web TO mc_web;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA web TO mc_web;

-- Lecture seule sur minecraft et discord
GRANT SELECT ON ALL TABLES IN SCHEMA minecraft TO mc_web;
GRANT SELECT ON ALL TABLES IN SCHEMA discord TO mc_web;
GRANT SELECT ON public.users TO mc_web;

-- Mise à jour limitée des users (profil)
GRANT UPDATE (username, avatar_url, settings) ON public.users TO mc_web;

-- Permissions par défaut
ALTER DEFAULT PRIVILEGES IN SCHEMA web GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mc_web;

-- ============================================
-- SECTION 6: PERMISSIONS mc_admin
-- ============================================

-- Accès complet à tous les schemas
GRANT ALL PRIVILEGES ON SCHEMA public, minecraft, discord, web, logs TO mc_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mc_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA minecraft TO mc_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA discord TO mc_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA web TO mc_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA logs TO mc_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public, minecraft, discord, web, logs TO mc_admin;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public, minecraft, discord, web, logs TO mc_admin;

-- Permissions par défaut pour mc_admin
ALTER DEFAULT PRIVILEGES GRANT ALL PRIVILEGES ON TABLES TO mc_admin;
ALTER DEFAULT PRIVILEGES GRANT ALL PRIVILEGES ON SEQUENCES TO mc_admin;
ALTER DEFAULT PRIVILEGES GRANT ALL PRIVILEGES ON FUNCTIONS TO mc_admin;

-- ============================================
-- SECTION 7: CRÉATION DES UTILISATEURS APPLICATIFS
-- ============================================

-- Utilisateur pour le bot (hérite de mc_bot)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{{PROJECT_NAME_LOWER}}_bot_user') THEN
        CREATE USER {{PROJECT_NAME_LOWER}}_bot_user WITH PASSWORD '{{POSTGRES_BOT_PASSWORD}}';
        GRANT mc_bot TO {{PROJECT_NAME_LOWER}}_bot_user;
    END IF;
END
$$;

-- Utilisateur pour le web (hérite de mc_web)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{{PROJECT_NAME_LOWER}}_web_user') THEN
        CREATE USER {{PROJECT_NAME_LOWER}}_web_user WITH PASSWORD '{{POSTGRES_WEB_PASSWORD}}';
        GRANT mc_web TO {{PROJECT_NAME_LOWER}}_web_user;
    END IF;
END
$$;

-- Utilisateur readonly pour monitoring (hérite de mc_readonly)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{{PROJECT_NAME_LOWER}}_readonly_user') THEN
        CREATE USER {{PROJECT_NAME_LOWER}}_readonly_user WITH PASSWORD '{{POSTGRES_READONLY_PASSWORD}}';
        GRANT mc_readonly TO {{PROJECT_NAME_LOWER}}_readonly_user;
    END IF;
END
$$;

-- ============================================
-- SECTION 8: ROW LEVEL SECURITY (RLS)
-- ============================================

-- Activer RLS sur les tables sensibles
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE web.sessions ENABLE ROW LEVEL SECURITY;

-- Politique: Les utilisateurs ne peuvent voir que leur propre profil (pour le web)
CREATE POLICY users_self_access ON public.users
    FOR ALL
    TO mc_web
    USING (
        -- Permet l'accès si l'utilisateur est le propriétaire OU si c'est une lecture
        id::text = current_setting('app.current_user_id', true)
        OR current_setting('app.is_admin', true) = 'true'
    );

-- Politique: Sessions uniquement pour le propriétaire
CREATE POLICY sessions_self_access ON web.sessions
    FOR ALL
    TO mc_web
    USING (
        user_id::text = current_setting('app.current_user_id', true)
    );

-- Les rôles admin et bot contournent RLS
ALTER TABLE public.users FORCE ROW LEVEL SECURITY;
ALTER TABLE web.sessions FORCE ROW LEVEL SECURITY;

-- Exempter mc_bot et mc_admin de RLS
ALTER ROLE mc_bot BYPASSRLS;
ALTER ROLE mc_admin BYPASSRLS;

-- ============================================
-- SECTION 9: AUDIT DES CHANGEMENTS DE PERMISSIONS
-- ============================================

-- Fonction pour auditer les changements de rôle utilisateur
CREATE OR REPLACE FUNCTION audit_role_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND OLD.role IS DISTINCT FROM NEW.role THEN
        INSERT INTO logs.audit (
            action,
            target_type,
            target_id,
            target_identifier,
            description,
            old_value,
            new_value,
            severity
        ) VALUES (
            'role_change',
            'user',
            NEW.id::TEXT,
            COALESCE(NEW.username, NEW.discord_id::TEXT),
            format('Changement de rôle: %s -> %s', OLD.role, NEW.role),
            jsonb_build_object('role', OLD.role),
            jsonb_build_object('role', NEW.role),
            'warning'
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger pour auditer les changements de rôle
DROP TRIGGER IF EXISTS trigger_audit_role_changes ON public.users;
CREATE TRIGGER trigger_audit_role_changes
    AFTER UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION audit_role_changes();

-- ============================================
-- SECTION 10: CONTRAINTES DE SÉCURITÉ ADDITIONNELLES
-- ============================================

-- Limiter les connexions par utilisateur
ALTER ROLE {{PROJECT_NAME_LOWER}}_bot_user CONNECTION LIMIT 20;
ALTER ROLE {{PROJECT_NAME_LOWER}}_web_user CONNECTION LIMIT 50;
ALTER ROLE {{PROJECT_NAME_LOWER}}_readonly_user CONNECTION LIMIT 10;

-- Timeout des requêtes pour éviter les DoS
ALTER ROLE mc_readonly SET statement_timeout = '30s';
ALTER ROLE mc_bot SET statement_timeout = '60s';
ALTER ROLE mc_web SET statement_timeout = '30s';

-- ============================================
-- SECTION 11: COMMENTAIRES DE DOCUMENTATION
-- ============================================

COMMENT ON ROLE mc_readonly IS 'Rôle lecture seule pour monitoring et analytics';
COMMENT ON ROLE mc_bot IS 'Rôle pour le bot Discord - lecture/écriture minecraft, discord, logs';
COMMENT ON ROLE mc_web IS 'Rôle pour l''application web - accès complet au schema web';
COMMENT ON ROLE mc_admin IS 'Rôle administrateur - accès complet à tous les schemas';
