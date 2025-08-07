from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `attachment_jp` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `hiragana` VARCHAR(60) COMMENT '假名',
    `romaji` LONGTEXT COMMENT '罗马字',
    `record` VARCHAR(120) COMMENT '发音',
    `pic` VARCHAR(120) COMMENT '配图',
    `word_id` INT NOT NULL,
    CONSTRAINT `fk_attachme_wordlist_c6aaf942` FOREIGN KEY (`word_id`) REFERENCES `wordlist_jp` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `attachment_jp`;"""
