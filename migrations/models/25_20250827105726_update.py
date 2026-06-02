from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `pos_type` MODIFY COLUMN `pos_type` VARCHAR(30) NOT NULL COMMENT 'noun: 名词\nadj: 形容词\nadj_v: 形容动词\nadv: 连用\nv1: 一段动词\nv5: 五段动词\nhelp: 助词\nself: 自动词\nother: 他动词\ntail: 接尾\nself_other: 自他动词\nfollow: 接续\nhabit: 惯用\nexcl: 感叹词\nka_v: カ变动词\nsa_v: サ变动词\nconn: 连体\nquantity: 量词\npron: 代词';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `pos_type` MODIFY COLUMN `pos_type` VARCHAR(30) NOT NULL COMMENT 'noun: 名词\nadj: 形容词\nadj_v: 形容动词\nv1: 一段动词\nv5: 五段动词\nhelp: 助词\nself: 自动词\nother: 他动词\ntail: 接尾\nself_other: 自他动词\nfollow: 接续词\nhabit: 惯用\nexcl: 感叹词\nka_v: カ变动词\nsa_v: サ变动词\nconn: 连体\nquantity: 量词';"""
