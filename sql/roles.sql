-- Run through python -m assistant.setup_role. Password never enters this file.
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'assistant_ro') THEN
        CREATE ROLE assistant_ro LOGIN;
    END IF;
END $$;
ALTER ROLE assistant_ro NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
ALTER ROLE assistant_ro SET default_transaction_read_only = on;
ALTER ROLE assistant_ro SET statement_timeout = '20s';
ALTER ROLE assistant_ro SET lock_timeout = '2s';
ALTER ROLE assistant_ro SET idle_in_transaction_session_timeout = '25s';
ALTER ROLE assistant_ro SET search_path = pg_catalog;
