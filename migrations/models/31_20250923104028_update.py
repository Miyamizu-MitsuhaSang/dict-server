from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` ADD `email` VARCHAR(120) COMMENT 'e-mail';
        ALTER TABLE `users` ADD `phone` VARCHAR(11) NOT NULL COMMENT '用户手机号';
        ALTER TABLE `users` ALTER COLUMN `portrait` SET DEFAULT '#';
        ALTER TABLE `comments_jp` ADD `supervised` BOOL NOT NULL DEFAULT 0;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` DROP COLUMN `email`;
        ALTER TABLE `users` DROP COLUMN `phone`;
        ALTER TABLE `users` ALTER COLUMN `portrait` DROP DEFAULT;
        ALTER TABLE `comments_jp` DROP COLUMN `supervised`;"""
