from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `definitions_fr` RENAME COLUMN `part_of_speech` TO `pos`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `definitions_fr` RENAME COLUMN `pos` TO `part_of_speech`;"""
