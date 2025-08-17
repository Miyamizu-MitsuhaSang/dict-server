from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `wordlist_fr` ADD `freq` INT NOT NULL;
        ALTER TABLE `wordlist_fr` ADD `search_text` VARCHAR(255) NOT NULL;
        ALTER TABLE `wordlist_fr` ADD INDEX `idx_wordlist_fr_search__5455f1` (`search_text`);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `wordlist_fr` DROP INDEX `idx_wordlist_fr_search__5455f1`;
        ALTER TABLE `wordlist_fr` DROP COLUMN `freq`;
        ALTER TABLE `wordlist_fr` DROP COLUMN `search_text`;"""
