from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `definitions_fr` MODIFY COLUMN `pos` VARCHAR(30) COMMENT 'n: n.\nn_f: n.f.\nn_f_pl: n.f.pl.\nn_m: n.m.\nn_m_pl: n.m.pl.\nv: v.\nv_t: v.t.\nv_i: v.i.\nv_pr: v.pr.\nv_t_i: v.t./v.i.\nadj: adj.\nadv: adv.\nprep: prep.\npron: pron.\nconj: conj.\ninterj: interj.\nchauff: chauff';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `definitions_fr` MODIFY COLUMN `pos` VARCHAR(30) NOT NULL COMMENT 'n: n.\nn_f: n.f.\nn_f_pl: n.f.pl.\nn_m: n.m.\nn_m_pl: n.m.pl.\nv: v.\nv_t: v.t.\nv_i: v.i.\nv_pr: v.pr.\nv_t_i: v.t./v.i.\nadj: adj.\nadv: adv.\nprep: prep.\npron: pron.\nconj: conj.\ninterj: interj.\nchauff: chauff';"""
