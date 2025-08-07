from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `language` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(30) NOT NULL UNIQUE,
    `code` VARCHAR(10) NOT NULL UNIQUE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `reserved_words` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `reserved` VARCHAR(20) NOT NULL COMMENT '保留词',
    `category` VARCHAR(20) NOT NULL DEFAULT 'username'
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(20) NOT NULL UNIQUE COMMENT '用户名',
    `pwd_hashed` VARCHAR(60) NOT NULL COMMENT '密码',
    `portrait` VARCHAR(120) NOT NULL COMMENT '用户头像',
    `is_admin` BOOL NOT NULL COMMENT '管理员权限' DEFAULT 0,
    `language_id` INT NOT NULL,
    CONSTRAINT `fk_users_language_d51b5368` FOREIGN KEY (`language_id`) REFERENCES `language` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `wordlist` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `language` VARCHAR(20) NOT NULL COMMENT '单词语种',
    `text` VARCHAR(40) NOT NULL UNIQUE COMMENT '单词'
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `attachment` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `yinbiao` VARCHAR(60) COMMENT '音标',
    `record` VARCHAR(120) COMMENT '发音',
    `pic` VARCHAR(120) COMMENT '配图',
    `word_id` INT NOT NULL,
    CONSTRAINT `fk_attachme_wordlist_ca554ed9` FOREIGN KEY (`word_id`) REFERENCES `wordlist` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `definitions` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `part_of_speech` VARCHAR(20) COMMENT '词性',
    `meaning` LONGTEXT NOT NULL COMMENT '单词释义',
    `example` LONGTEXT COMMENT '单词例句',
    `eng_explanation` LONGTEXT COMMENT 'English explanation',
    `target_language_id` INT NOT NULL,
    `word_id` INT NOT NULL,
    CONSTRAINT `fk_definiti_language_9d3d9ce0` FOREIGN KEY (`target_language_id`) REFERENCES `language` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_definiti_wordlist_551d1753` FOREIGN KEY (`word_id`) REFERENCES `wordlist` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(100) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
