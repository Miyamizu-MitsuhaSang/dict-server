from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        SET @has_col := (
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'users'
              AND COLUMN_NAME = 'email'
        );
        SET @ddl := IF(
            @has_col = 1,
            'ALTER TABLE `users` MODIFY COLUMN `email` VARCHAR(120) NULL COMMENT ''e-mail''',
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
              AND COLUMN_NAME = 'email'
        );
        SET @ddl := IF(
            @has_col = 1,
            'ALTER TABLE `users` MODIFY COLUMN `email` VARCHAR(120) NOT NULL COMMENT ''e-mail''',
            'SELECT 1'
        );
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    """
