ALTER TABLE apartments ADD COLUMN id bigint GENERATED ALWAYS AS IDENTITY UNIQUE;

CREATE TABLE apartment_residents (
    apartment_id bigint PRIMARY KEY REFERENCES apartments(id) ON DELETE CASCADE,
    resident_id text NOT NULL
);
CREATE INDEX apartment_residents_by_account ON apartment_residents (resident_id, apartment_id);

INSERT INTO apartment_residents (apartment_id, resident_id)
SELECT id, resident_id FROM apartments WHERE resident_id IS NOT NULL;

ALTER TABLE apartments DROP COLUMN resident_id, DROP COLUMN initial_resident_name;

ALTER TABLE reservations
    ADD COLUMN start_time time(0),
    ADD COLUMN end_time time(0),
    ADD CONSTRAINT reservation_hours_valid CHECK (
        (start_time IS NULL AND end_time IS NULL)
        OR (start_time IS NOT NULL AND end_time IS NOT NULL AND start_time < end_time)
    );

ALTER TABLE visits
    ADD COLUMN entry_time time(0),
    ADD COLUMN exit_time time(0),
    ADD CONSTRAINT visit_hours_valid CHECK (
        exit_time IS NULL OR (entry_time IS NOT NULL AND entry_time < exit_time)
    );
