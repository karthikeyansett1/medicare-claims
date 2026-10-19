-- OWNER-ONLY, ONE-TIME SETUP. A preexisting schema or role aborts the transaction.
-- No DROP, TRUNCATE, DELETE, UPDATE-reset, or ON CONFLICT reinitialization exists.
BEGIN;
CREATE ROLE medicare_live_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT medicare_live_owner TO CURRENT_USER;
CREATE SCHEMA live_budget AUTHORIZATION medicare_live_owner;
REVOKE ALL ON SCHEMA live_budget FROM PUBLIC;
SET LOCAL ROLE medicare_live_owner;
CREATE TABLE live_budget.campaign (
  singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
  campaign_id text NOT NULL UNIQUE CHECK (campaign_id='sample1-fixture-live-v1'),
  cap_microdollars bigint NOT NULL CHECK (cap_microdollars=5000000),
  spent_microdollars bigint NOT NULL DEFAULT 0 CHECK (spent_microdollars BETWEEN 0 AND 5000000)
);
INSERT INTO live_budget.campaign VALUES (true,'sample1-fixture-live-v1',5000000,0);
CREATE TABLE live_budget.reservations (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  input_bound integer NOT NULL,
  output_bound integer NOT NULL,
  microdollars bigint NOT NULL CHECK (microdollars>0)
);
CREATE FUNCTION live_budget.reserve(request_campaign text, input_bound integer, output_bound integer, requested_microdollars bigint)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,live_budget AS $$
DECLARE current_spend bigint; required_cost bigint; reservation_id bigint;
BEGIN
  IF request_campaign IS DISTINCT FROM 'sample1-fixture-live-v1'
     OR input_bound IS NULL OR input_bound NOT BETWEEN 8192 AND 70000
     OR output_bound IS NULL OR output_bound NOT BETWEEN 1 AND 3000 THEN
    RAISE EXCEPTION 'Invalid reservation bounds';
  END IF;
  required_cost := ceil(input_bound::numeric*12.5+output_bound::numeric*50)::bigint;
  IF requested_microdollars IS DISTINCT FROM required_cost THEN
    RAISE EXCEPTION 'Invalid reservation cost';
  END IF;
  -- One persistent row serializes every replica. The lock lasts until COMMIT.
  SELECT spent_microdollars INTO current_spend FROM live_budget.campaign
    WHERE singleton AND campaign_id=request_campaign AND cap_microdollars=5000000 FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Campaign unavailable'; END IF;
  IF current_spend+required_cost>5000000 THEN RAISE EXCEPTION 'Lifetime allowance exhausted'; END IF;
  IF (SELECT count(*) FROM live_budget.reservations WHERE created_at>clock_timestamp()-interval '1 minute')>=3
     OR (SELECT count(*) FROM live_budget.reservations WHERE created_at>clock_timestamp()-interval '24 hours')>=30 THEN
    RAISE EXCEPTION 'Shared request rate limit reached';
  END IF;
  UPDATE live_budget.campaign SET spent_microdollars=spent_microdollars+required_cost WHERE singleton;
  INSERT INTO live_budget.reservations(input_bound,output_bound,microdollars)
    VALUES(input_bound,output_bound,required_cost) RETURNING id INTO reservation_id;
  RETURN reservation_id;
END $$;
CREATE FUNCTION live_budget.status()
RETURNS TABLE(campaign_id text,cap_microdollars bigint,spent_microdollars bigint)
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,live_budget AS $$
  SELECT campaign_id,cap_microdollars,spent_microdollars FROM live_budget.campaign WHERE singleton
$$;
REVOKE ALL ON ALL TABLES IN SCHEMA live_budget FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA live_budget FROM PUBLIC;
REVOKE ALL ON FUNCTION live_budget.reserve(text,integer,integer,bigint),live_budget.status() FROM PUBLIC;
RESET ROLE;
CREATE ROLE medicare_live_budget LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT USAGE ON SCHEMA live_budget TO medicare_live_budget;
GRANT EXECUTE ON FUNCTION live_budget.reserve(text,integer,integer,bigint),live_budget.status() TO medicare_live_budget;
REVOKE ALL ON SCHEMA live_budget FROM medicare_demo_ro;
REVOKE ALL ON FUNCTION live_budget.reserve(text,integer,integer,bigint),live_budget.status() FROM medicare_demo_ro;
COMMIT;
