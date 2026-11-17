CREATE TABLE apartments (
    number text PRIMARY KEY,
    resident_id text,
    CHECK (number ~ '^[0-9]{1,10}[A-Z]?$')
);
CREATE INDEX apartments_by_resident ON apartments (resident_id, number);

CREATE TABLE areas (
    id text PRIMARY KEY,
    name text NOT NULL,
    fee_cents integer NOT NULL CHECK (fee_cents BETWEEN 0 AND 100000000),
    CHECK (id ~ '^[a-z0-9]+(-[a-z0-9]+)*$')
);
CREATE UNIQUE INDEX areas_distinct_name ON areas (lower(name));

CREATE TABLE regulations (
    version integer PRIMARY KEY CHECK (version >= 0),
    content text NOT NULL,
    author_id text,
    author_name text,
    published_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reservations (
    code text PRIMARY KEY,
    apartment text NOT NULL REFERENCES apartments(number) ON DELETE RESTRICT ON UPDATE RESTRICT,
    resident_id text,
    area_id text NOT NULL REFERENCES areas(id) ON DELETE RESTRICT,
    date date NOT NULL,
    fee_cents integer NOT NULL CHECK (fee_cents BETWEEN 0 AND 100000000),
    status text NOT NULL CHECK (status IN ('active', 'cancelled'))
);
CREATE UNIQUE INDEX reservations_active_slot ON reservations (area_id, date) WHERE status = 'active';
CREATE INDEX reservations_by_apartment ON reservations (apartment, resident_id, date);

CREATE TABLE visits (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    apartment text NOT NULL REFERENCES apartments(number) ON DELETE RESTRICT ON UPDATE RESTRICT,
    resident_id text,
    name text NOT NULL,
    date date NOT NULL
);
CREATE INDEX visits_by_apartment ON visits (apartment, resident_id, date);

CREATE TABLE chat_sessions (
    id uuid PRIMARY KEY,
    apartment text NOT NULL REFERENCES apartments(number) ON DELETE RESTRICT ON UPDATE RESTRICT,
    resident_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX chat_sessions_by_resident ON chat_sessions (resident_id, created_at);
