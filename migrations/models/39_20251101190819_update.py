from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `user_test_record` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `username` VARCHAR(20) NOT NULL,
    `language` VARCHAR(10) NOT NULL,
    `total_sentences` INT NOT NULL,
    `average_score` DOUBLE NOT NULL,
    `accuracy_score` DOUBLE NOT NULL,
    `fluency_score` DOUBLE NOT NULL,
    `completeness_score` DOUBLE NOT NULL,
    `level` VARCHAR(20) NOT NULL,
    `raw_result` JSON NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_user_tes_users_243f3b0b` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `pronunciationtest_jp` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `text` LONGTEXT NOT NULL COMMENT '朗读文段'
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `pronunciationtest_jp`;
        DROP TABLE IF EXISTS `user_test_record`;"""
