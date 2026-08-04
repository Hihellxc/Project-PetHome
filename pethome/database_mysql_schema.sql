-- PetHome Database Schema (MySQL version)
-- ใช้คำสั่งนี้ถ้าต้องการรันบน MySQL แทน SQLite
-- วิธีใช้: mysql -u root -p < database_mysql_schema.sql

CREATE DATABASE IF NOT EXISTS pethome;
USE pethome;

CREATE TABLE User (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE Pet (
    pet_id INT AUTO_INCREMENT PRIMARY KEY,
    owner_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    gender VARCHAR(20) NOT NULL,
    age INT NOT NULL,
    province VARCHAR(100) NOT NULL,
    description TEXT,
    image VARCHAR(255),
    status VARCHAR(20) DEFAULT 'Available',
    created_at DATETIME,
    FOREIGN KEY (owner_id) REFERENCES User(user_id)
);

CREATE TABLE Adoption (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    pet_id INT NOT NULL,
    user_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    message TEXT,
    status VARCHAR(20) DEFAULT 'Pending',
    created_at DATETIME,
    FOREIGN KEY (pet_id) REFERENCES Pet(pet_id)
);

-- หมายเหตุ: ถ้าใช้ MySQL จริง ให้เปลี่ยนใน app.py จาก sqlite3
-- เป็น mysql-connector-python หรือ PyMySQL แทน
