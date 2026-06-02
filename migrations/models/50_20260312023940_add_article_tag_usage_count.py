from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `article_tags` ADD `usage_count` INT NOT NULL DEFAULT 0;
        UPDATE `article_tags` t
        SET `usage_count` = (
            SELECT COUNT(*)
            FROM `articles` a
            WHERE JSON_CONTAINS(a.`tags`, JSON_QUOTE(t.`name`), '$')
        );"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `article_tags` DROP COLUMN `usage_count`;"""
