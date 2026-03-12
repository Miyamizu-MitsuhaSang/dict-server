# Lexiverse Dict Server

一个面向小语种学习者的多功能学习平台后端，整合法语/日语词典、AI 辅助、作文指导、发音测评与翻译等能力，为 Web 与移动端提供统一的 API 服务。

**文档版本**：2.0  
**最后更新**：2026-03-12

## 功能速览
- **多语词典**：精确检索、联想提示、谚语/成语等扩展词库，并支持后台批量导入、编辑。
- **学习助手**：AI 释义、作文批改、发音测评和评论互动，结合 Redis 记录上下文与进度。
- **安全体系**：JWT 认证、Redis 黑名单、邮箱 & 手机找回、管理员权限隔离。
- **周边工具**：站内反馈、翻译速率限制、搜索量统计与 Redis 健康检查。

## 架构概述
```
客户端 ⇆ FastAPI Router
              ├─ User / Auth
              ├─ Dictionary Search
              ├─ Admin Dictionary
              ├─ AI Assist & Article Director
              ├─ Pronunciation Test
              └─ Utility / Feedback / Translator
                 ↓
        Tortoise ORM  →  MySQL
        Redis (state, caches, rate-limit)
        外部服务：邮件、Azure Speech、AI/翻译 API
```

## 目录结构
- `app/api/*`：各模块路由与服务层实现
- `app/models`：Tortoise ORM 数据模型
- `app/core`：Redis、邮件、重置逻辑等基础设施
- `docs/api.md`：完整接口文档（本仓库主文档）
- `settings.py`：环境配置（数据库、Redis、第三方 Key）
- `migrations/`：数据库迁移记录

## 环境依赖
- Python 3.11+
- MySQL 8.x
- Redis 6+
- 需配置的外部服务：邮件 SMTP、Azure Speech、AI/翻译 API Key

## 快速开始
1. 安装依赖：`pip install -r requirements.txt`
2. 配置 `settings.py`（数据库、Redis、邮件、第三方 Key）并初始化 `.env`
3. 运行迁移：`aerich upgrade`（或项目内自定义脚本）
4. 启动服务：`python main.py`
5. 访问交互式文档：`http://127.0.0.1:8000/docs`

## 开发与测试
- **代码风格**：PEP 8 + FastAPI 推荐实践；异步 IO 优先。
- **校验**：Pydantic 模型负责请求体验证；业务规则放在 `service.py`。
- **测试建议**：结合 pytest/HTTPX 进行路由测试，可使用虚拟 Redis。
- **调试**：默认启用 CORS + Uvicorn reload；注意不要提交 `.env`。

## 运维要点
- Uvicorn/Gunicorn 部署在 Nginx `/api` 反向代理之后，务必同步前缀。
- Redis 用于登录黑名单、验证码、限流、发音测评上下文，需设置持久化策略。
- 管理员接口需要 `is_admin_user` 依赖；生产环境建议通过 RBAC/网关再加一层。
- 重要指标：词典检索耗时、AI 调用成功率、发音测评存储量、邮件/验证码发送失败率。

## 1.0 版本记录（2025）
- 基础账号体系：用户注册、登录、登出、资料修改与找回密码流程（邮箱/手机）。
- 词典核心能力：法语/日语词条检索、联想列表、谚语/成语检索。
- 后台词典管理：词条查询、批量调整、新增释义、Excel 导入。
- 学习辅助能力：AI 释义问答、作文指导（Article Director）、发音测评。
- 通用功能：翻译接口、反馈接口、Redis 健康检查、搜索统计与重置。
- 基础安全与架构：JWT 鉴权、Redis 黑名单、FastAPI + Tortoise ORM + MySQL + Redis。

## 2.0 版本更新（2026-03-12）
- 文章模块升级：新增文章来源字段 `articles.source`，并同步到后台/前台文章模型与接口响应。
- 封面图能力升级：新增 `POST /admin/article/{article_id}/cover/upload`，支持本地上传、服务端落盘与数据库记录同步。
- 后台文章管理完善：支持创建、编辑保存、发布、取消发布、删除、轮播开关、Tag 搜索与新增。
- 轮播管理增强：新增 `POST /admin/article/{article_id}/banner/switch`，并限制同时最多 4 个激活轮播。
- 前台内容接口完善：新增文章分页列表、文章详情、热门 Tags（`/culture_share/article/list`、`/culture_share/article/{article_id}`、`/culture_share/tags`）。
- Tag 统计能力：`article_tags` 新增 `usage_count`，在文章创建/更新/删除后自动刷新“被多少文章使用”的计数。
- 鉴权策略更新：除 `GET /culture_share/banners` 外，文章相关接口均需登录；`/admin/*` 统一管理员依赖校验。
- 数据迁移：已升级至 `50_20260312023940_add_article_tag_usage_count.py`。

## 文档
- **详细 API**：`docs/api.md`
- **安全/流程设计**：`display/*.puml` PlantUML 图

## 贡献
欢迎通过 Issue/PR 反馈问题或提交功能。提交前请：
1. 确认通过 lint/测试；
2. 在 PR 描述中说明修改动机与测试结果；
3. 如涉及接口变更，同步更新 `docs/api.md`。

---
Lexiverse 团队 · 2025
