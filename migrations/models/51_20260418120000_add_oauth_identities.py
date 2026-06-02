from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `oauth_identities` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `provider` VARCHAR(20) NOT NULL COMMENT '第三方登录提供方',
    `openid` VARCHAR(128) NOT NULL COMMENT '开放平台 openid',
    `unionid` VARCHAR(128) COMMENT '开放平台 unionid',
    `profile` JSON COMMENT '第三方用户资料快照',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_oauth_id_users_3f9306a1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `uid_oauth_iden_provide_4fa514` UNIQUE KEY (`provider`, `openid`),
    KEY `idx_oauth_identity_provider_unionid` (`provider`, `unionid`)
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `oauth_identities`;"""
