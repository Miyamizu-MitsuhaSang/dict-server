from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `proverb_fr` RENAME COLUMN `proverb` TO `text`;
        ALTER TABLE `proverb_fr` DROP COLUMN `updated_at`;
        ALTER TABLE `idiom_jp` ADD `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `idiom_jp` DROP COLUMN `created_at`;
        ALTER TABLE `proverb_fr` RENAME COLUMN `text` TO `proverb`;
        ALTER TABLE `proverb_fr` ADD `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);"""
