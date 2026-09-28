ALTER TABLE pets
    ADD INDEX idx_pets_status (status),
    ADD INDEX idx_pets_filters (species, province, status),
    ADD INDEX idx_pets_created_at (created_at);