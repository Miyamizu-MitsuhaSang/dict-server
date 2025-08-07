from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        RENAME TABLE `definitions` TO `definitions_fr`;
        CREATE TABLE IF NOT EXISTS `definition_jp` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `meaning` LONGTEXT NOT NULL COMMENT '单词释义',
    `example` LONGTEXT COMMENT '单词例句',
    `pos` VARCHAR(30) COMMENT 'noun: 名词\nadj: 形容词\nadj_v: 形容动词\nv1: 一段动词\nv5: 五段动词\nhelp: 助词',
    `word_id` INT NOT NULL,
    CONSTRAINT `fk_definiti_wordlist_9093dbd0` FOREIGN KEY (`word_id`) REFERENCES `wordlist_jp` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        DROP TABLE IF EXISTS `definitions`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `definition_jp`;
        DROP TABLE IF EXISTS `definitions_fr`;"""
