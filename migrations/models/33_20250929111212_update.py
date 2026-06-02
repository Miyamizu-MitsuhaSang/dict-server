from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` MODIFY COLUMN `encrypted_phone` VARCHAR(11) NULL COMMENT '用户手机号';
        ALTER TABLE `users` MODIFY COLUMN `email` VARCHAR(120) NOT NULL COMMENT 'e-mail';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` MODIFY COLUMN `encrypted_phone` VARCHAR(11) NOT NULL COMMENT '用户手机号';
        ALTER TABLE `users` MODIFY COLUMN `email` VARCHAR(120) COMMENT 'e-mail';"""
