from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `pronunciationtest_fr` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `text` LONGTEXT NOT NULL COMMENT '朗读文段'
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `pronunciationtest_fr`;"""
