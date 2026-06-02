from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `definition_fr` RENAME TO `definitions_fr`;
        ALTER TABLE `wordlist_fr` ALTER COLUMN `freq` SET DEFAULT 0;
        ALTER TABLE `wordlist_jp` ADD `hiragana` VARCHAR(60) NOT NULL COMMENT '假名';
        ALTER TABLE `wordlist_jp` ADD `freq` INT NOT NULL DEFAULT 0;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `wordlist_fr` ALTER COLUMN `freq` DROP DEFAULT;
        ALTER TABLE `wordlist_jp` DROP COLUMN `hiragana`;
        ALTER TABLE `wordlist_jp` DROP COLUMN `freq`;
        ALTER TABLE `definitions_fr` RENAME TO `definition_fr`;"""
