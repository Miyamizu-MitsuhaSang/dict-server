from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `wordlist_fr` DROP COLUMN `language`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `wordlist_fr` ADD `language` VARCHAR(20) NOT NULL COMMENT '单词语种';"""
