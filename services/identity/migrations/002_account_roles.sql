ALTER TABLE accounts DROP CONSTRAINT accounts_role_check;

UPDATE accounts SET role = 'admin' WHERE role = 'superuser';
UPDATE accounts SET name = 'Administração auxiliar'
WHERE id = 'demo-super' AND name = 'Superusuário' AND role = 'admin';

ALTER TABLE accounts ADD CONSTRAINT accounts_role_check CHECK (role IN ('admin', 'resident'));
