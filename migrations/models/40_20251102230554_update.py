from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `idiom_jp` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `text` LONGTEXT NOT NULL,
    `chi_exp` LONGTEXT NOT NULL,
    `example` LONGTEXT NOT NULL,
    `search_text` LONGTEXT NOT NULL
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `idiom_jp`;"""
