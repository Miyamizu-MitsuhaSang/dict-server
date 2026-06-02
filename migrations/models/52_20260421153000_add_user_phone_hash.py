from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        SET @has_col := (
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'users'
              AND COLUMN_NAME = 'phone_hash'
        );
        SET @ddl := IF(
            @has_col = 0,
            'ALTER TABLE `users` ADD COLUMN `phone_hash` VARCHAR(64) NULL COMMENT ''手机号查询哈希'', ADD UNIQUE KEY `uid_users_phone_hash` (`phone_hash`)',
            'SELECT 1'
        );
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        SET @has_col := (
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'users'
              AND COLUMN_NAME = 'phone_hash'
        );
        SET @ddl := IF(
            @has_col = 1,
            'ALTER TABLE `users` DROP INDEX `uid_users_phone_hash`, DROP COLUMN `phone_hash`',
            'SELECT 1'
        );
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    """
