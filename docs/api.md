# FastAPI  
版本：0.1.0

**认证方式**  
除特别说明外，接口均需要在 Header 中携带 `Authorization: Bearer <token>`。

------

## User API

### Register
**Method**: `POST`  
**Path**: `/users/register`

#### 请求体
| 字段      | 类型                                           | 必填 | 说明 |
|-----------|------------------------------------------------|------|------|
| username  | string                                         | 是   | 3-20 位，首字符需为字母/下划线，仅允许字母、数字、下划线且不能命中保留关键词 |
| password  | string                                         | 是   | 6-20 位，至少包含 1 个数字，仅允许大小写字母、数字和常见特殊字符 |
| email     | string                                         | 是   | 需要先通过 `/users/register/email_verify` 获取验证码 |
| code      | string                                         | 是   | 邮箱验证码，5 分钟有效，验证成功后立即失效 |
| phone     | string                                         | 否   | 中国大陆 11 位手机号，若不填则为 `null` |
| lang_pref | string(enum: jp, fr, private，默认: private)   | 否   | 语言偏好，值必须是系统已存在的语言 code |
| portrait  | string(默认: #)                                | 否   | 头像 URL |

#### 响应
**200 成功**  
| 字段         | 类型   | 说明 |
|--------------|--------|------|
| id           | int    | 新用户 ID |
| message      | string | 固定为 `register success` |
| access_token | string | JWT 访问令牌，20 小时有效 |
| token_type   | string | 固定为 `bearer` |

**400 业务错误**  
`用户名为保留关键词，请更换`、`用户名长度必须在3到20个字符之间`、`密码...`、`验证码错误或已过期`、`用户名已经被占用` 等。

**422 验证错误**  
返回 `HTTPValidationError`

---

### Request Email Verification Code
**Method**: `POST`  
**Path**: `/users/register/email_verify`

#### 请求体
| 字段  | 类型   | 必填 | 说明          |
|-------|--------|------|---------------|
| email | string | 是   | 未注册过的邮箱 |

#### 响应
- **200**：`{"message": "验证码已发送"}`  
- **400**：邮箱已被使用

---

### Login
**Method**: `POST`  
**Path**: `/users/login`

#### 请求体
| 字段    | 类型   | 必填 | 说明     |
|---------|--------|------|----------|
| name    | string | 是   | 用户名   |
| password| string | 是   | 登录密码 |

#### 响应
**200 成功**：返回 `access_token`、`token_type` 以及用户信息 `{id, username, is_admin, lang_pref}`。  
**404**：用户不存在  
**400**：用户名或密码错误

---

### Logout
**Method**: `POST`  
**Path**: `/users/logout`  
需要认证

#### 响应
- **200**：`{"message": "logout ok"}`  
- **401**：未携带有效的 Bearer Token

---

### Update Profile
**Method**: `PUT`  
**Path**: `/users/update`  
需要认证

#### 请求体
| 字段             | 类型                                  | 必填 | 说明 |
|------------------|---------------------------------------|------|------|
| current_password | string                                | 是   | 用于确认身份 |
| new_username     | string                                | 否   | 新用户名，需遵守注册规则且不能为保留词 |
| new_password     | string                                | 否   | 新密码，需遵守注册规则 |
| new_language     | string(enum: jp, fr, private，默认: private) | 否 | 新语言偏好 |

#### 响应
- **200**：修改成功（无返回体）  
- **400**：原密码错误或新用户名为保留关键词  
- **422**：字段校验失败

---

### Forgot Password (Phone) — Deprecated
**Method**: `POST`  
**Path**: `/users/auth/forget-password/phone`

#### 请求体
| 字段        | 类型 | 必填 | 说明 |
|-------------|------|------|------|
| phone_number| string | 是 | 中国大陆手机号 |

返回 `{"message": "验证码已发送"}`。若手机号不存在，则 404。

---

### Verify Phone Code — Deprecated
**Method**: `POST`  
**Path**: `/users/auth/varify_code`

#### 请求体
| 字段 | 类型   | 必填 | 说明   |
|------|--------|------|--------|
| code | string | 是   | 验证码 |
| phone| string | 是   | 手机号 |

#### 响应
- **200**：`{"message": "验证成功，可以重置密码"}`  
- **400**：验证码错误或过期

---

### Forgot Password (Email)
**Method**: `POST`  
**Path**: `/users/auth/forget-password/email`

#### 请求体
| 字段  | 类型   | 必填 | 说明 |
|-------|--------|------|------|
| email | string | 是   | 已注册邮箱 |

#### 响应
- **200**：验证码发送成功  
- **404**：邮箱未注册

---

### Verify Email Reset Code
**Method**: `POST`  
**Path**: `/users/auth/varify_code/email`

#### 请求体
| 字段  | 类型   | 必填 | 说明   |
|-------|--------|------|--------|
| email | string | 是   | 邮箱地址 |
| code  | string | 是   | 邮箱验证码 |

#### 响应
- **200**：`{"reset_token": "<token>"}`（后续重置密码需要将该 token 放在 `X-Reset-Token` 头部）  
- **400**：验证码错误或已过期

---

### Reset Password
**Method**: `POST`  
**Path**: `/users/auth/reset-password`

#### Headers
| 名称          | 说明                            |
|---------------|---------------------------------|
| X-Reset-Token | `/users/auth/varify_code/email` 返回的 token |

#### 请求体
| 字段    | 类型   | 必填 | 说明                   |
|---------|--------|------|------------------------|
| password| string | 是   | 新密码（与注册规则一致） |

#### 响应
- **200**：`{"massage": "密码重置成功"}`  
- **400**：密码不符合规则或者 token 无效

------

## Admin Dictionary API
所有接口都需要管理员身份（`is_admin_user` 依赖）。

### List Dictionary Entries
**Method**: `GET`  
**Path**: `/admin/dict`

#### Query
| 参数      | 类型                    | 默认 | 说明                           |
|-----------|-------------------------|------|--------------------------------|
| page      | integer (>=1)           | 1    | 页码                            |
| page_size | integer (<=10)          | 10   | 每页条数                        |
| lang_code | string(enum: fr, jp)    | fr   | 选择法语或日语词典数据          |

#### 响应
`{"total": <总数>, "data": [ ...词条... ]}`

---

### Search Word (Admin)
**Method**: `POST`  
**Path**: `/admin/dict/search_word`

#### 请求体
`SearchWordRequest`：`word`、`language`(fr/jp)、可选 `pos`。  
#### 响应
匹配到的定义数组；若单词不存在则 400。

---

### Batch Adjust Definitions
**Method**: `PUT`  
**Path**: `/admin/dict/adjust`

#### 请求体
`UpdateWordSet`（包含若干 `UpdateWord`，字段 `id`, `word`, `language`, 以及需要修改的定义字段）。  

#### 响应
返回 `success_count`、`fail_count` 与失败详情。  
422 表示没有任何改动；400/404 表示部分更新失败。

---

### Add Definition
**Method**: `POST`  
**Path**: `/admin/dict/add`

#### 请求体
`CreateWord`：`word`、`language`、`pos`、`meaning`、`example`、`eng_explanation`（法语必填、日语不可填）。  

#### 响应
- **200**：创建成功  
- **409**：释义已存在  
- **400**：不支持的语言

---

### Import via Excel
**Method**: `POST`  
**Path**: `/admin/dict/update_by_xlsx`

#### 请求体
| 字段 | 类型      | 必填 | 说明                        |
|------|-----------|------|-----------------------------|
| file | UploadFile| 是   | `.xlsx` / `.xls` 文件       |

#### 响应
- **200**：`{"message": "导入成功"}`  
- **400**：文件格式错误  
- **500**：导入失败（返回具体原因）

------

## Culture Share API
前缀：`/culture_share`。  
`/culture_share/banners` 默认无需认证；其余文章相关接口需要登录认证。

### Home Banners
**Method**: `GET`  
**Path**: `/culture_share/banners`

#### Query
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| limit | integer(2-5) | 4 | 轮播展示数量 |

#### 响应
`{"article_cnt": <数量>, "article_list": [{id, title, subtitle, image_url, target_url, sort_order, is_active, start_at, end_at}, ...]}`

---

### Popular Tags
**Method**: `GET`  
**Path**: `/culture_share/tags`
需要认证

#### Query
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| limit | integer(1-100) | 10 | 返回前 N 个高频 tags |

#### 响应
`{"total": <总数>, "items": [{"tag_id", "name", "usage_count"}, ...]}`

按 `usage_count`（被多少篇文章使用）降序返回。

---

### Article List
**Method**: `GET`  
**Path**: `/culture_share/article/list`
需要认证

#### Query
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | integer(>=1) | 1 | 页码 |
| page_size | integer(1-50) | 10 | 每页条数 |
| category | string | - | 分类精确筛选 |
| keyword | string | - | 标题模糊搜索 |

#### 响应
`{"page": 1, "page_size": 10, "total": 123, "items": [{article_id, title, summary, source, cover_url, category, tags, publish_at, created_at}, ...]}`

仅返回 `published` 且 `publish_at <= 当前时间`（或 `publish_at` 为空）的文章。

---

### Article Detail
**Method**: `GET`  
**Path**: `/culture_share/article/{article_id}`
需要认证

#### 响应
- **200**：`{article_id, title, summary, source, cover_url, content_html, content_text, category, tags, publish_at, created_at, updated_at}`  
- **404**：文章不存在或未发布

------

## Admin Article API
前缀：`/admin/article`，需管理员认证。

### Create Article
**Method**: `POST`  
**Path**: `/admin/article/create_article`

#### 请求体
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 标题 |
| summary | string | 否 | 摘要 |
| source | string | 否 | 文章来源/出处 |
| cover_url | string | 否 | 封面 URL（也可后续通过上传接口覆盖） |
| content_html | string | 是 | 富文本正文 |
| content_text | string | 否 | 纯文本正文，不传则后端从 `content_html` 提取 |
| tags | string[] | 否 | 标签数组（自动去重清洗并同步到 `article_tags`） |
| category | string | 否 | 分类 |
| status | enum(`draft`/`published`) | 否 | 默认 `draft` |
| publish_at | datetime | 否 | 发布时间，`status=published` 且不传时自动补当前时间 |

#### 响应
`{"message": "文章创建成功", "article_id": "<id>"}`

---

### Update Article (Edit & Save)
**Method**: `PUT`  
**Path**: `/admin/article/{article_id}`

#### 请求体
与创建文章一致，当前实现为“全量更新”：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 标题 |
| summary | string | 否 | 摘要 |
| source | string | 否 | 文章来源/出处 |
| cover_url | string | 否 | 封面 URL；传空会覆盖当前值 |
| content_html | string | 是 | 富文本正文 |
| content_text | string | 否 | 纯文本正文，不传则后端从 `content_html` 提取 |
| tags | string[] | 否 | 标签数组（自动去重清洗并同步到 `article_tags`） |
| category | string | 否 | 分类 |
| status | enum(`draft`/`published`) | 是 | 文章状态 |
| publish_at | datetime | 否 | 发布时间 |

#### 保存逻辑（后端自动处理）
- 当 `status=published` 且 `publish_at` 未传时：
  如果文章已有发布时间则沿用，否则自动补当前时间。
- `tags` 会自动 `strip + 去重`，并写入 `article_tags` 表。
- 正文会先进行 HTML 清洗，再存储。

#### 响应
- **200**：`{"message": "文章更新成功", "article_id": "<id>"}`
- **404**：文章不存在

---

### Get Article List
**Method**: `GET`  
**Path**: `/admin/article`

#### Query
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | integer(>=1) | 1 | 页码 |
| page_size | integer(1-100) | 10 | 每页条数 |
| status | string | - | 状态筛选 |
| category | string | - | 分类筛选 |
| keyword | string | - | 标题模糊搜索 |

#### 响应
`{"items": [{article_id, title, summary, source, cover_url, category, tags, status, publish_at, created_at, updated_at}, ...], "total": <总数>}`

---

### Get Article Detail
**Method**: `GET`  
**Path**: `/admin/article/{article_id}`

#### 响应
- **200**：`{article_id, title, summary, source, cover_url, content_html, content_text, category, tags, status, publish_at, created_at, updated_at}`  
- **404**：文章不存在

---

### Get Published Status
**Method**: `GET`  
**Path**: `/admin/article/{article_id}/published`

#### 响应
- **200**：`{"article_id": "<id>", "status": "draft|published", "is_published": <bool>, "publish_at": "<datetime|null>"}`  
- **404**：文章不存在

---

### Get Banner Status
**Method**: `GET`  
**Path**: `/admin/article/{article_id}/banner`

#### 响应
- **200**：`{"article_id": "<id>", "has_banner": <bool>, "enabled": <bool>, "banner_id": <int|null>, "sort_order": <int|null>, "start_at": "<datetime|null>", "end_at": "<datetime|null>"}`  
- **404**：文章不存在

---

### Publish Article
**Method**: `POST`  
**Path**: `/admin/article/{article_id}/publish`

#### 响应
`{"message": "文章发布成功", "article_id": "<id>"}`

> 该功能可由 `Update Article` 复用：将 `status` 设为 `published` 即可达到发布效果。  
> 保留本接口是为了在“只切换发布状态”时调用更轻量。

---

### Unpublish Article
**Method**: `POST`  
**Path**: `/admin/article/{article_id}/unpublish`

#### 响应
`{"message": "文章已撤回为草稿", "article_id": "<id>"}`

> 该功能同样可由 `Update Article` 复用：将 `status` 设为 `draft` 即可。

---

### Delete Article
**Method**: `DELETE`  
**Path**: `/admin/article/{article_id}`

#### 响应
- **200**：`{"message": "文章删除成功", "article_id": "<id>"}`
- **404**：文章不存在

#### 删除行为
- 删除 `articles` 文章记录
- 删除该文章关联的 `article_pics` 记录及对应本地图片文件
- 删除该文章关联的 `banner` 记录
- 清理首页轮播缓存

---

### Switch Banner
**Method**: `POST`  
**Path**: `/admin/article/{article_id}/banner/switch`

#### 请求体
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| enabled | bool | 是 | `true` 开启轮播，`false` 关闭轮播 |
| title | string | 否 | 轮播标题，不传默认文章标题 |
| subtitle | string | 否 | 轮播副标题，不传默认文章摘要 |
| image_url | string | 否 | 轮播图地址，不传默认文章 `cover_url`；若仍为空则由前端兜底默认图 |
| target_url | string | 否 | 点击跳转地址，不传默认 `/culture_share/article/{article_id}` |
| sort_order | integer | 否 | 排序值，默认 `0` |
| start_at | datetime | 否 | 生效开始时间 |
| end_at | datetime | 否 | 生效结束时间 |

#### 响应
`{"message": "轮播已开启/轮播已关闭", "article_id": "<id>", "banner_id": <id|null>, "enabled": <bool>}`

#### 约束
- 同时激活的轮播最多 4 个。  
- 当调用开启轮播（`enabled=true`）且当前已激活轮播数达到 4 个时，接口返回 400：  
`当前已存在4个轮播，请先取消其他文章的轮播后再开启`

---

### Upload Cover Image
**Method**: `POST`  
**Path**: `/admin/article/{article_id}/cover/upload`

#### 请求体
`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | UploadFile | 是 | 封面图片文件，支持 `jpg/jpeg/png/webp/gif` |

#### 响应
`{"message": "封面上传成功", "article_id": "<id>", "cover_url": "/media/article/covers/YYYYMM/cover_<articleid>_<timestamp>_<rand>.<ext>", "pic_id": "<pic_id>"}`  
同时会更新：
- `articles.cover_url`（可直接给前端展示）
- `article_pics` 中该文章 `is_cover=true` 的记录（不存在则创建，存在则覆盖）

#### 存储规则
- 目录：`<项目根目录>/media/article/covers/YYYYMM/`
- 文件名：`cover_{article_id去掉-}_{yyyyMMddHHmmss}_{8位随机串}.{ext}`

---

### Search Tags
**Method**: `GET`  
**Path**: `/admin/article/tag/search`

#### Query
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| keyword | string | - | 按 tag 名模糊查询 |
| limit | integer(1-100) | 20 | 返回条数上限 |

#### 响应
`{"items": [{"tag_id", "name", "created_at", "updated_at"}, ...], "total": <总数>}`

---

### Create Tag
**Method**: `POST`  
**Path**: `/admin/article/tag`

#### 请求体
`{"name": "历史文化"}`

#### 响应
`{"tag_id": "...", "name": "历史文化", "created_at": "...", "updated_at": "..."}`

> 文章创建/更新时，`tags` 字段会自动去重清洗并同步写入 `article_tags` 表。

------

## AI Assist API

### Explain Word
**Method**: `POST`  
**Path**: `/ai_assist/word/exp`  
需要认证

#### 请求体
| 字段   | 类型   | 必填 | 说明         |
|--------|--------|------|--------------|
| word   | string | 是   | 目标词汇     |
| question| string| 是   | 关于该词的问题 |

#### 响应
`AIAnswerOut`：`word`、`answer`（经过后处理）、`model`、`tokens_used`。  
当用户当月使用次数超过 100 且非管理员时返回 400。调用第三方 AI 失败则 500。

---

### Clear Word Chat History
**Method**: `POST`  
**Path**: `/ai_assist/clear`  
需要认证

#### 请求体
| 字段 | 类型   | 必填 | 说明      |
|------|--------|------|-----------|
| word | string | 是   | 要清除的词 |

#### 响应
`{"msg": "已清除 <word> 的聊天记录"}`

> `/ai_assist/univer` 暂未实现，调用会返回空响应。

------

## Article Director API

### Submit Article
**Method**: `POST`  
**Path**: `/article-director/article`  
需要认证

#### Query
`lang`：`en-US` / `fr-FR` / `ja-JP`，默认 `fr-FR`。

#### 请求体
| 字段        | 类型   | 必填 | 说明                 |
|-------------|--------|------|----------------------|
| theme       | string | 否   | 文章主题             |
| content     | string | 是   | 完整文章内容         |
| article_type| string | 是   | 作文类型             |

#### 响应
`{"reply": <指导>, "tokens": <用量>, "conversation_length": <当前上下文长度>}`。  
接口会自动维护 Redis 会话，上游需要在调用后再调用 reset。

---

### Follow-up Question
**Method**: `POST`  
**Path**: `/article-director/question`  
需要认证

#### 请求体
| 字段 | 类型   | 必填 | 说明   |
|------|--------|------|--------|
| query| string | 是   | 追问内容 |

#### 响应
同上，返回最新回答、tokens 与对话长度。

---

### Reset Conversation
**Method**: `POST`  
**Path**: `/article-director/reset`  
需要认证

#### 响应
`{"message": "已重置用户 <id> 的作文对话记录"}`

------

## Feedback API

### Submit Feedback
**Method**: `POST`  
**Path**: `/improvements`  
需要认证

#### 请求体
| 字段       | 类型   | 必填 | 说明 |
|------------|--------|------|------|
| report_part| enum   | 是   | `ui_design` / `dict_fr` / `dict_jp` / `user` / `translate` / `writting` / `ai_assist` / `pronounce`（`comment_api_test` 仅测试用） |
| text       | string | 是   | 反馈内容 |

#### 响应
`{"massages": "feedback succeed"}`，同时触发邮件通知。

------

## Pronunciation Test API
前缀：`/test/pron`，均需认证。

### Start Test
**Method**: `GET`  
**Path**: `/test/pron/start`

#### Query / Form
| 参数 | 类型                | 默认 | 说明                         |
|------|---------------------|------|------------------------------|
| count| integer             | 20   | 需要的句子数量               |
| lang | string(enum: fr-FR, ja-JP) | fr-FR | 语言（通过 `Form` 读取） |

#### 响应
`{"ok": True, "resumed": <bool>, "session": {"lang": ..., "current_index": ..., "sentence_ids": [...], "total": ...}}`

---

### Submit Sentence Recording
**Method**: `POST`  
**Path**: `/test/pron/sentence_test`

#### 请求体
| 字段  | 类型      | 必填 | 说明                      |
|-------|-----------|------|---------------------------|
| record| UploadFile| 是   | `.wav` 音频文件           |
| lang  | string(enum: fr-FR, ja-JP) | 是 | 语言（Form 字段） |

#### 响应
成功时：`{"ok": True, "data": {...评分... , "progress": "X/Y"}}`。  
无会话返回 `{"ok": False, "error": "No active test session"}`；音频格式/评分失败返回 400/415。

---

### Get Current Sentence
**Method**: `GET`  
**Path**: `/test/pron/current_sentence`

#### 响应
- 有会话：`{"ok": True, "index": <idx>, "current_sentence": "<text>"}`  
- 无会话：`{"ok": False, "error": "No active test session"}`

---

### Get Test Sentence List
**Method**: `POST`  
**Path**: `/test/pron/testlist`

返回会话中的句子数组 `[{id, text}, ...]`，若无会话则错误同上。

---

### Finish Test
**Method**: `POST`  
**Path**: `/test/pron/finish`

#### 请求体
| 字段   | 类型  | 必填 | 说明                        |
|--------|-------|------|-----------------------------|
| confirm| bool  | 否   | 当测试未完成时是否强制结束（Form 字段，默认 False） |

#### 响应
- 未开始：`{"ok": False, "message": "No active test session to finish"}`  
- 未完成且未确认：返回剩余数量提示  
- 强制结束：`{"ok": True, "forced_end": True, "data": {...}}`  
- 全部完成：返回 `{"ok": True, "data": {...}}` 并写入数据库

---

### Clear Session
**Method**: `POST`  
**Path**: `/test/pron/clear_session`

#### 响应
`{"ok": True, "message": "Session cleared"}`

------

## Dictionary Search API

### Exact Word Search
**Method**: `POST`  
**Path**: `/search/word`  
需要认证

#### 请求体
`SearchRequest`：`query`、`language`(fr/jp)、`sort`(relevance/date)、`order`(asc/des)。  

#### 响应
`WordSearchResponse`：`query`、`pos`、`contents`（按语言返回对应结构），日语额外返回 `hiragana`。  
404 表示词条不存在。

---

### Suggest Word List
**Method**: `POST`  
**Path**: `/search/list/word`  
需要认证

#### 请求体
同 `SearchRequest`。

#### 响应
`{"list": [<候选词/释义> ...]}`，根据语言自动混合联想与释义匹配。

---

### Suggest Proverbs
**Method**: `POST`  
**Path**: `/search/list/proverb`

#### 请求体
`ProverbSearchRequest`：`query`、`dict_language`(默认 fr)。

#### 响应
`{"list": [...]}`，按语言返回谚语候选。

---

### Get Proverb Detail
**Method**: `POST`  
**Path**: `/search/proverb`

#### 请求体
| 字段     | 类型 | 必填 | 说明        |
|----------|------|------|-------------|
| proverb_id | int | 是   | 谚语 ID（Form 字段） |

#### 响应
`{"result": {"id": ..., "text": ..., "chi_exp": ...}}`

---

### Suggest Idioms
**Method**: `POST`  
**Path**: `/search/list/idiom`

#### 请求体
`ProverbSearchRequest`（`dict_language` 仅允许 `jp`）。  
服务会进行语言检测、假名转换和多策略匹配。

#### 响应
`{"list": [{"text": ..., "search_text": ..., ...}, ...]}`，顺序与匹配策略保持一致。

---

### Get Idiom Detail
**Method**: `POST`  
**Path**: `/search/idiom`

#### 请求体
| 字段   | 类型 | 必填 | 说明 |
|--------|------|------|------|
| query_id | int | 是 | 成语 ID |

#### 响应
`{"result": {"id": ..., "text": ..., "search_text": ..., "chi_exp": ..., "example": ...}}`

------

## Translator API

### Translate
**Method**: `POST`  
**Path**: `/translate`  
需要认证，且默认开启速率限制（同用户在 1 秒内最多 2 次）。

#### 请求体
| 字段      | 类型                             | 默认 | 说明                                   |
|-----------|----------------------------------|------|----------------------------------------|
| query     | string                           | 是   | 待翻译文本                             |
| from_lang | enum(auto, fra, jp, zh, en)      | auto | 源语言                                 |
| to_lang   | enum(fra, jp, zh, en)            | zh   | 目标语言（不可为 auto，且不能与 from 相同） |

#### 响应
`{"translated_text": "<结果>"}`。  
第三方 API 报错会转为 400。

---

### Translate (Debug)
**Method**: `POST`  
**Path**: `/translate/debug`  
仅管理员可用，受同样的速率限制。

#### Query
| 参数 | 默认 | 说明          |
|------|------|---------------|
| query| -    | 待翻译文本    |
| from_lang | auto | 源语言 |
| to_lang | zh | 目标语言 |

#### 响应
与正式接口一致。

------

## Word Comment API

### Create Word Comment
**Method**: `POST`  
**Path**: `/comment/word/{lang}`  
需要认证

#### Path
| 参数 | 说明           |
|------|----------------|
| lang | `fr` 或 `jp`   |

#### 请求体
| 字段          | 类型   | 必填 | 说明           |
|---------------|--------|------|----------------|
| comment_word  | string | 是   | 关联的单词文本 |
| comment_content | string | 是 | 评论内容       |

#### 响应
200（空体）。评论会记录用户 ID 与语言。

------

## Util API

### Get Search Count
**Method**: `GET`  
**Path**: `/search_time`

#### 响应
`{"count": <int>}`，若首次访问会初始化为 0。

---

### Reset Search Count
**Method**: `GET`  
**Path**: `/search/reset`

#### 响应
`{"message": "search times reset successfully"}`

------

## Redis Test API

### Ping Redis
**Method**: `GET`  
**Path**: `/ping-redis`

#### 响应
`{"pong": true, "redis": {...连接参数...}}`

------

## 错误模型

### ValidationError

| 字段 | 类型                    | 必填 | 说明       |
| ---- | ----------------------- | ---- | ---------- |
| loc  | array[string / integer] | 是   | Location   |
| msg  | string                  | 是   | Message    |
| type | string                  | 是   | Error Type |

### HTTPValidationError

| 字段   | 类型                   | 必填 | 说明   |
| ------ | ---------------------- | ---- | ------ |
| detail | array[ValidationError] | 否   | Detail |
