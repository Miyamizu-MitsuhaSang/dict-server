from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `comments_fr` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `comment_text` LONGTEXT NOT NULL COMMENT 'The comment text',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `comment_word_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_comments_wordlist_e5e7ea78` FOREIGN KEY (`comment_word_id`) REFERENCES `wordlist_fr` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_comments_users_5003adfc` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `comments_jp` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `comment_text` LONGTEXT NOT NULL COMMENT 'The comment text',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `comment_word_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_comments_wordlist_04781cd3` FOREIGN KEY (`comment_word_id`) REFERENCES `wordlist_jp` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_comments_users_32553072` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `comments_improving` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `comment_text` LONGTEXT NOT NULL COMMENT 'The comment text',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_comments_users_7b1878d3` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `comments_fr`;
        DROP TABLE IF EXISTS `comments_jp`;
        DROP TABLE IF EXISTS `comments_improving`;"""
