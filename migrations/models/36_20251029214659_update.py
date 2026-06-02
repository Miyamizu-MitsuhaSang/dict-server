from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE `wordlist_fr_proverb_fr` (
    `proverbfr_id` INT NOT NULL REFERENCES `proverb_fr` (`id`) ON DELETE CASCADE,
    `wordlist_fr_id` INT NOT NULL REFERENCES `wordlist_fr` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `wordlist_fr_proverb_fr`;"""
