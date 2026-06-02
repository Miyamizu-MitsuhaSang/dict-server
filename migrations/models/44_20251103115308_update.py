from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `kangji_mapping_zh_jp` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `hanzi` LONGTEXT NOT NULL,
    `kangji` LONGTEXT NOT NULL,
    `note` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `kangji_mapping_zh_jp`;"""
