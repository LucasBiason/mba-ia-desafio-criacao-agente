CREATE TABLE IF NOT EXISTS accounts (
    id text PRIMARY KEY,
    name text NOT NULL CHECK (length(name) BETWEEN 1 AND 120),
    email text NOT NULL UNIQUE,
    password_hash text NOT NULL,
    role text NOT NULL CHECK (role IN ('admin', 'resident')),
    active boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS sessions (
    id text PRIMARY KEY,
    account_id text NOT NULL REFERENCES accounts(id),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz
);
CREATE INDEX IF NOT EXISTS sessions_by_account ON sessions (account_id);

CREATE TABLE IF NOT EXISTS login_limits (
    key text PRIMARY KEY,
    window_start timestamptz NOT NULL,
    attempts integer NOT NULL CHECK (attempts > 0)
);

CREATE TABLE IF NOT EXISTS identity_seed (
    only_row boolean PRIMARY KEY DEFAULT true CHECK (only_row)
);

CREATE TABLE IF NOT EXISTS identity_migrations (
    version integer PRIMARY KEY
);
