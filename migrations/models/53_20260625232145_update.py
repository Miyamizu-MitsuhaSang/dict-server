from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` ADD `id_number` VARCHAR(18) COMMENT '身份证号';
        ALTER TABLE `users` MODIFY COLUMN `email` VARCHAR(120) COMMENT 'e-mail';
        CREATE TABLE IF NOT EXISTS `article_director_call_logs` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `request_id` VARCHAR(36) NOT NULL UNIQUE COMMENT '请求追踪ID',
    `login_type` VARCHAR(30) COMMENT '登录方式',
    `endpoint` VARCHAR(120) NOT NULL COMMENT '调用接口',
    `method` VARCHAR(10) NOT NULL COMMENT 'HTTP 方法',
    `client_ip` VARCHAR(64) COMMENT '客户端 IP',
    `user_agent` VARCHAR(512) COMMENT 'User-Agent',
    `action` VARCHAR(30) NOT NULL COMMENT '写作指导动作',
    `lang` VARCHAR(20) COMMENT '请求语言代码',
    `article_lang` VARCHAR(20) COMMENT '作文语言',
    `article_type` VARCHAR(60) COMMENT '作文体裁',
    `theme` VARCHAR(255) COMMENT '作文标题或主题',
    `input_text` LONGTEXT COMMENT '发送给模型的用户输入',
    `input_hash` VARCHAR(64) COMMENT '用户输入 SHA-256',
    `input_length` INT NOT NULL COMMENT '用户输入长度' DEFAULT 0,
    `output_text` LONGTEXT COMMENT '模型回复',
    `output_hash` VARCHAR(64) COMMENT '模型回复 SHA-256',
    `output_length` INT COMMENT '模型回复长度',
    `provider` VARCHAR(50) NOT NULL COMMENT '模型服务提供方' DEFAULT 'ECNU EduChat',
    `model` VARCHAR(50) NOT NULL COMMENT '模型名称' DEFAULT 'educhat-r1',
    `base_url` VARCHAR(255) NOT NULL COMMENT '模型服务地址',
    `temperature` DOUBLE COMMENT 'temperature 参数',
    `top_p` DOUBLE COMMENT 'top_p 参数',
    `system_prompt_hash` VARCHAR(64) COMMENT '系统提示词 SHA-256',
    `message_count` INT NOT NULL COMMENT '本次上游消息数量' DEFAULT 0,
    `conversation_length_before` INT NOT NULL COMMENT '调用前上下文长度' DEFAULT 0,
    `conversation_length_after` INT COMMENT '调用后上下文长度',
    `upstream_request_id` VARCHAR(120) COMMENT '上游请求或响应 ID',
    `prompt_tokens` INT COMMENT '输入 token 数',
    `completion_tokens` INT COMMENT '输出 token 数',
    `total_tokens` INT COMMENT '总 token 数',
    `latency_ms` INT COMMENT '上游调用耗时毫秒',
    `status` VARCHAR(20) NOT NULL COMMENT '调用状态',
    `error_code` VARCHAR(120) COMMENT '错误类型',
    `error_message` LONGTEXT COMMENT '脱敏错误信息',
    `risk_flags` JSON COMMENT '内容安全与风控标记',
    `blocked` BOOL NOT NULL COMMENT '是否拦截' DEFAULT 0,
    `policy_version` VARCHAR(50) COMMENT '合规策略版本',
    `retention_months` INT NOT NULL COMMENT '日志留存月数' DEFAULT 6,
    `expires_at` DATETIME(6) NOT NULL COMMENT '日志到期时间',
    `created_at` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_article__users_8bd6597f` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_article_dir_user_id_c623c9` (`user_id`, `created_at`),
    KEY `idx_article_dir_expires_5336ae` (`expires_at`),
    KEY `idx_article_dir_status_e02a63` (`status`, `created_at`)
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` DROP COLUMN `id_number`;
        ALTER TABLE `users` MODIFY COLUMN `email` VARCHAR(120) NOT NULL COMMENT 'e-mail';
        DROP TABLE IF EXISTS `article_director_call_logs`;"""
