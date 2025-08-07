from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        RENAME TABLE 'fr_wordlist' TO 'wordlist_fr';
        CREATE TABLE IF NOT EXISTS `wordlist_jp` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `text` VARCHAR(40) NOT NULL COMMENT '单词'
) CHARACTER SET utf8mb4;
           """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `attachment_fr`;
        DROP TABLE IF EXISTS `wordlist_jp`;
        DROP TABLE IF EXISTS `wordlist_fr`;"""
