from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` MODIFY COLUMN `encrypted_phone` VARCHAR(128) COMMENT '用户手机号';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` MODIFY COLUMN `encrypted_phone` VARCHAR(11) COMMENT '用户手机号';"""
