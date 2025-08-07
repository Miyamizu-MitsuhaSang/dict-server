from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `definitions_fr` DROP FOREIGN KEY `fk_definiti_language_9d3d9ce0`;
        ALTER TABLE `definitions_fr` DROP COLUMN `target_language_id`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `definitions_fr` ADD `target_language_id` INT NOT NULL;
        ALTER TABLE `definitions_fr` ADD CONSTRAINT `fk_definiti_language_82dc7bd0` FOREIGN KEY (`target_language_id`) REFERENCES `language` (`id`) ON DELETE CASCADE;"""
