UPDATE pets SET status = 'available' WHERE status = 'pending';

ALTER TABLE pets
    MODIFY COLUMN status ENUM('available', 'adopted', 'rejected') NOT NULL DEFAULT 'available';