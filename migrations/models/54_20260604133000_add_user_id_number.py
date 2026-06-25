from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        SET @has_col := (
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'users'
              AND COLUMN_NAME = 'id_number'
        );
        SET @ddl := IF(
            @has_col = 0,
            'ALTER TABLE `users` ADD COLUMN `id_number` VARCHAR(18) NULL COMMENT ''身份证号''',
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
              AND COLUMN_NAME = 'id_number'
        );
        SET @ddl := IF(
            @has_col = 1,
            'ALTER TABLE `users` DROP COLUMN `id_number`',
            'SELECT 1'
        );
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    """
