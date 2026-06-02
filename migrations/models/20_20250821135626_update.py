from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `definitions_fr` RENAME TO `definition_fr`;
        ALTER TABLE `definition_fr` ADD `example_varification` BOOL NOT NULL COMMENT '例句是否审核' DEFAULT 0;
        ALTER TABLE `definition_fr` MODIFY COLUMN `pos` VARCHAR(30) COMMENT 'n: n.\nn_f: n.f.\nn_f_pl: n.f.pl.\nn_m: n.m.\nn_m_pl: n.m.pl.\nv: v.\nv_t: v.t.\nv_i: v.i.\nv_pr: v.pr.\nv_t_i: v.t./v.i.\nv_t_dir: v.t.dir.\nv_t_ind: v.t.ind.\nv_t_pr: v.t.(v.pr.)\nv_i_ind: v.t.ind./v.i.\nadj: adj.\nadv: adv.\nprep: prep.\npron: pron.\nconj: conj.\ninterj: interj.\nchauff: chauff\nart: art.';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `definition_fr` RENAME TO `definitions_fr`;
        ALTER TABLE `definition_fr` DROP COLUMN `example_varification`;
        ALTER TABLE `definition_fr` MODIFY COLUMN `pos` VARCHAR(30) COMMENT 'n: n.\nn_f: n.f.\nn_f_pl: n.f.pl.\nn_m: n.m.\nn_m_pl: n.m.pl.\nv: v.\nv_t: v.t.\nv_i: v.i.\nv_pr: v.pr.\nv_t_i: v.t./v.i.\nadj: adj.\nadv: adv.\nprep: prep.\npron: pron.\nconj: conj.\ninterj: interj.\nchauff: chauff';"""
