from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `proverb_fr` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `proverb` LONGTEXT NOT NULL COMMENT '法语谚语及常用表达',
    `chi_exp` LONGTEXT NOT NULL COMMENT '中文释义',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `proverb_fr`;"""
