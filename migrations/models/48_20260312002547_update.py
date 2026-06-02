from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `language` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(30) NOT NULL UNIQUE,
    `code` VARCHAR(10) NOT NULL UNIQUE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `reserved_words` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `reserved` VARCHAR(20) NOT NULL COMMENT '保留词',
    `category` VARCHAR(20) NOT NULL DEFAULT 'username'
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `users` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(20) NOT NULL COMMENT '用户名',
    `pwd_hashed` VARCHAR(60) NOT NULL COMMENT '密码',
    `portrait` VARCHAR(120) NOT NULL COMMENT '用户头像' DEFAULT '#',
    `email` VARCHAR(120) NOT NULL UNIQUE COMMENT 'e-mail',
    `encrypted_phone` VARCHAR(128) COMMENT '用户手机号',
    `is_admin` BOOL NOT NULL COMMENT '管理员权限' DEFAULT 0,
    `token_usage` INT NOT NULL COMMENT 'AI答疑使用量' DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL COMMENT '注册时间' DEFAULT CURRENT_TIMESTAMP(6),
    `language_id` INT NOT NULL,
    CONSTRAINT `fk_users_language_d51b5368` FOREIGN KEY (`language_id`) REFERENCES `language` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `user_test_record` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `username` VARCHAR(20) NOT NULL,
    `language` VARCHAR(10) NOT NULL,
    `total_sentences` INT NOT NULL,
    `average_score` DOUBLE NOT NULL,
    `accuracy_score` DOUBLE NOT NULL,
    `fluency_score` DOUBLE NOT NULL,
    `completeness_score` DOUBLE NOT NULL,
    `level` VARCHAR(20) NOT NULL,
    `raw_result` JSON NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_user_tes_users_243f3b0b` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `attachment_fr` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `yinbiao` VARCHAR(60) COMMENT '音标',
    `record` VARCHAR(120) COMMENT '发音',
    `pic` VARCHAR(120) COMMENT '配图',
    `word_id` INT NOT NULL,
    CONSTRAINT `fk_attachme_wordlist_d43c7eb0` FOREIGN KEY (`word_id`) REFERENCES `wordlist_fr` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `definitions_fr` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `pos` VARCHAR(30) COMMENT 'n: n.\nn_f: n.f.\nn_f_pl: n.f.pl.\nn_m: n.m.\nn_m_pl: n.m.pl.\nv: v.\nv_t: v.t.\nv_i: v.i.\nv_pr: v.pr.\nv_t_i: v.t./v.i.\nv_t_dir: v.t.dir.\nv_t_ind: v.t.ind.\nv_t_pr: v.t.(v.pr.)\nv_i_ind: v.t.ind./v.i.\nadj: adj.\nadv: adv.\nprep: prep.\npron: pron.\nconj: conj.\ninterj: interj.\nchauff: chauff\nart: art.',
    `meaning` LONGTEXT NOT NULL COMMENT '单词释义',
    `example` LONGTEXT COMMENT '单词例句',
    `eng_explanation` LONGTEXT COMMENT 'English explanation',
    `example_varification` BOOL NOT NULL COMMENT '例句是否审核' DEFAULT 0,
    `word_id` INT NOT NULL,
    CONSTRAINT `fk_definiti_wordlist_0ea6942c` FOREIGN KEY (`word_id`) REFERENCES `wordlist_fr` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `pronunciationtest_fr` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `text` LONGTEXT NOT NULL COMMENT '朗读文段'
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `proverb_fr` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `text` LONGTEXT NOT NULL COMMENT '法语谚语及常用表达',
    `chi_exp` LONGTEXT NOT NULL COMMENT '中文释义',
    `freq` INT NOT NULL DEFAULT 0,
    `search_text` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `wordlist_fr` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `text` VARCHAR(40) NOT NULL UNIQUE COMMENT '单词',
    `freq` INT NOT NULL DEFAULT 0,
    `search_text` VARCHAR(255) NOT NULL,
    KEY `idx_wordlist_fr_search__5455f1` (`search_text`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `attachment_jp` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `hiragana` VARCHAR(60) COMMENT '假名',
    `romaji` LONGTEXT COMMENT '罗马字',
    `record` VARCHAR(120) COMMENT '发音',
    `pic` VARCHAR(120) COMMENT '配图',
    `word_id` INT NOT NULL,
    CONSTRAINT `fk_attachme_wordlist_c6aaf942` FOREIGN KEY (`word_id`) REFERENCES `wordlist_jp` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `definitions_jp` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `meaning` LONGTEXT NOT NULL COMMENT '单词释义',
    `example` LONGTEXT COMMENT '单词例句',
    `word_id` INT NOT NULL,
    CONSTRAINT `fk_definiti_wordlist_e63dd5e9` FOREIGN KEY (`word_id`) REFERENCES `wordlist_jp` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `idiom_jp` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `text` LONGTEXT NOT NULL,
    `chi_exp` LONGTEXT NOT NULL,
    `example` LONGTEXT NOT NULL,
    `search_text` LONGTEXT NOT NULL,
    `freq` INT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `kangji_mapping_zh_jp` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `hanzi` LONGTEXT NOT NULL,
    `kangji` LONGTEXT NOT NULL,
    `note` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `pos_type` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `pos_type` VARCHAR(30) NOT NULL COMMENT 'noun: 名词\nadj: 形容词\nadj_v: 形容动词\nadv: 连用\nv1: 一段动词\nv5: 五段动词\nhelp: 助词\nself: 自动词\nother: 他动词\ntail: 接尾\nself_other: 自他动词\nfollow: 接续\nhabit: 惯用\nexcl: 感叹词\nka_v: カ変\nsa_v: サ変\nconn: 连体\nquantity: 量词\npron: 代词'
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `pronunciationtest_jp` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `text` LONGTEXT NOT NULL COMMENT '朗读文段'
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `wordlist_jp` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `text` VARCHAR(40) NOT NULL COMMENT '单词',
    `hiragana` VARCHAR(60) NOT NULL COMMENT '假名',
    `freq` INT NOT NULL DEFAULT 0
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `comments_fr` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `comment_text` LONGTEXT NOT NULL COMMENT 'The comment text',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `supervised` BOOL NOT NULL DEFAULT 0,
    `comment_word_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_comments_wordlist_e5e7ea78` FOREIGN KEY (`comment_word_id`) REFERENCES `wordlist_fr` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_comments_users_5003adfc` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `comments_jp` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `comment_text` LONGTEXT NOT NULL COMMENT 'The comment text',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `supervised` BOOL NOT NULL DEFAULT 0,
    `comment_word_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_comments_wordlist_04781cd3` FOREIGN KEY (`comment_word_id`) REFERENCES `wordlist_jp` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_comments_users_32553072` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `comments_improving` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `comment_text` LONGTEXT NOT NULL COMMENT 'The comment text',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_comments_users_7b1878d3` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `articles` (
    `article_id` VARCHAR(255) NOT NULL PRIMARY KEY,
    `title` VARCHAR(255) NOT NULL,
    `summary` LONGTEXT,
    `source` LONGTEXT,
    `cover_url` VARCHAR(500),
    `content_html` LONGTEXT NOT NULL,
    `content_text` LONGTEXT,
    `category` VARCHAR(50),
    `tags` JSON NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'draft',
    `publish_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `article_pics` (
    `pic_id` VARCHAR(256) NOT NULL PRIMARY KEY,
    `sequence` INT NOT NULL DEFAULT 0,
    `pic_path` VARCHAR(256) NOT NULL COMMENT '图片存放路径',
    `is_cover` BOOL NOT NULL DEFAULT 0,
    `article_id` VARCHAR(255) NOT NULL,
    CONSTRAINT `fk_article__articles_b7b37346` FOREIGN KEY (`article_id`) REFERENCES `articles` (`article_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `article_tags` (
    `tag_id` VARCHAR(255) NOT NULL PRIMARY KEY,
    `name` VARCHAR(50) NOT NULL UNIQUE,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    KEY `idx_article_tag_name_4b7077` (`name`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `banner` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `title` VARCHAR(255) NOT NULL,
    `subtitle` VARCHAR(500),
    `image_url` VARCHAR(500) NOT NULL,
    `target_url` VARCHAR(500) NOT NULL,
    `sort_order` INT NOT NULL DEFAULT 0,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `start_at` DATETIME(6),
    `end_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `article_id` VARCHAR(255),
    CONSTRAINT `fk_banner_articles_99a331ad` FOREIGN KEY (`article_id`) REFERENCES `articles` (`article_id`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
        DROP TABLE IF EXISTS `sentence-Lite`;
        CREATE TABLE IF NOT EXISTS `wordlist_fr_proverb_fr` (
    `proverbfr_id` INT NOT NULL REFERENCES `proverb_fr` (`id`) ON DELETE CASCADE,
    `wordlist_fr_id` INT NOT NULL REFERENCES `wordlist_fr` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `definitions_jp_pos_type` (
    `definitions_jp_id` INT NOT NULL REFERENCES `definitions_jp` (`id`) ON DELETE CASCADE,
    `postype_id` INT NOT NULL REFERENCES `pos_type` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `idiom_jp`;
        DROP TABLE IF EXISTS `pronunciationtest_jp`;
        DROP TABLE IF EXISTS `article_pics`;
        DROP TABLE IF EXISTS `reserved_words`;
        DROP TABLE IF EXISTS `comments_improving`;
        DROP TABLE IF EXISTS `article_tags`;
        DROP TABLE IF EXISTS `attachment_jp`;
        DROP TABLE IF EXISTS `banner`;
        DROP TABLE IF EXISTS `proverb_fr`;
        DROP TABLE IF EXISTS `users`;
        DROP TABLE IF EXISTS `definitions_jp`;
        DROP TABLE IF EXISTS `user_test_record`;
        DROP TABLE IF EXISTS `language`;
        DROP TABLE IF EXISTS `attachment_fr`;
        DROP TABLE IF EXISTS `wordlist_fr`;
        DROP TABLE IF EXISTS `kangji_mapping_zh_jp`;
        DROP TABLE IF EXISTS `comments_jp`;
        DROP TABLE IF EXISTS `definitions_fr`;
        DROP TABLE IF EXISTS `articles`;
        DROP TABLE IF EXISTS `wordlist_jp`;
        DROP TABLE IF EXISTS `pos_type`;
        DROP TABLE IF EXISTS `comments_fr`;
        DROP TABLE IF EXISTS `pronunciationtest_fr`;"""
