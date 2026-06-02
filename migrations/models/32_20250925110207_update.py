from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` RENAME COLUMN `phone` TO `encrypted_phone`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` RENAME COLUMN `encrypted_phone` TO `phone`;"""
