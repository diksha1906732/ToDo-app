-- ═══════════════════════════════════════════
--  TASKR — MySQL Schema
--  Run this once to bootstrap the database
-- ═══════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS todo_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE todo_db;

CREATE TABLE IF NOT EXISTS todos (
    id          INT AUTO_INCREMENT PRIMARY KEY,
  user_id     INT                                NULL,
    title       VARCHAR(255)                        NOT NULL,
    description TEXT,
  category    VARCHAR(60)                         DEFAULT 'general',
    priority    ENUM('low', 'medium', 'high')       DEFAULT 'medium',
  due_date    DATE,
    completed   TINYINT(1)                          DEFAULT 0,
    alerted_at  DATETIME                            NULL,
    created_at  DATETIME                            DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME                            DEFAULT CURRENT_TIMESTAMP
                                                    ON UPDATE CURRENT_TIMESTAMP
);

-- Optional: seed data to verify the setup
INSERT INTO todos (user_id, title, description, category, priority, due_date) VALUES
  (NULL, 'Set up the project',   'Install dependencies and configure DB', 'work', 'high',   DATE_ADD(CURDATE(), INTERVAL 1 DAY)),
  (NULL, 'Read the README',      NULL,                                    'study', 'medium', CURDATE()),
  (NULL, 'Build something cool', 'Have fun with it',                      'personal', 'low', NULL);
