from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` ADD `token_usage` INT NOT NULL COMMENT 'AI答疑使用量' DEFAULT 0;
        ALTER TABLE `comments_fr` ADD `supervised` BOOL NOT NULL DEFAULT 0;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` DROP COLUMN `token_usage`;
        ALTER TABLE `comments_fr` DROP COLUMN `supervised`;"""
