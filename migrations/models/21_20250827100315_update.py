from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `definitions_jp` DROP COLUMN `pos`;
        CREATE TABLE IF NOT EXISTS `pos_type` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `pos_type` VARCHAR(30) NOT NULL COMMENT 'noun: 名词\nadj: 形容词\nadj_v: 形容动词\nv1: 一段动词\nv5: 五段动词\nhelp: 助词'
) CHARACTER SET utf8mb4;
        CREATE TABLE `definitions_jp_pos_type` (
    `definitions_jp_id` INT NOT NULL REFERENCES `definitions_jp` (`id`) ON DELETE CASCADE,
    `postype_id` INT NOT NULL REFERENCES `pos_type` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `definitions_jp_pos_type`;
        ALTER TABLE `definitions_jp` ADD `pos` VARCHAR(30) COMMENT 'noun: 名词\nadj: 形容词\nadj_v: 形容动词\nv1: 一段动词\nv5: 五段动词\nhelp: 助词';
        DROP TABLE IF EXISTS `pos_type`;"""
