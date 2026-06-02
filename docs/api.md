# FastAPI 接口文档
版本：2.1
最后更新：2026-04-21

本文档按当前代码实际挂载的路由整理，基于 [main.py](/Users/godrictan/Desktop/ECNU/双创/小语种词典/dict_server/main.py) 与各 `app/api/*/routes.py` 文件生成。

## 基本说明

### Base URL
- 本地开发：`http://127.0.0.1:8000`
- 线上前端当前使用：`https://lexiverse.com.cn/api`

### 认证方式
- 需要登录的接口，统一使用 Header：
  `Authorization: Bearer <access_token>`
- `refresh_token` 只能用于 `/users/refresh`，不能直接访问业务接口。

### 当前公开接口
以下接口当前代码允许匿名访问：
- `GET /culture_share/banners`
- `GET /culture_share/article/list`
- `GET /culture_share/article/{article_id}`
- `GET /culture_share/tags`
- `POST /search/word`
- `POST /search/list/word`
- `POST /search/list/proverb`
- `POST /search/proverb`
- `POST /search/list/idiom`
- `POST /search/idiom`
- `GET /miniapp/home`
- `GET /ping-redis`
- `GET /search_time`
- `GET /search/reset`

### 当前管理员接口
所有 `/admin/article/**` 接口都通过 [admin/router.py](/Users/godrictan/Desktop/ECNU/双创/小语种词典/dict_server/app/api/admin/router.py) 统一要求管理员权限。

### 额外说明
- `app/api/admin/dict.py` 中存在接口定义，但 **当前未在** [main.py](/Users/godrictan/Desktop/ECNU/双创/小语种词典/dict_server/main.py) **挂载**，不属于当前对外生效接口。
- 本文档只描述“当前代码实际可访问”的接口，不保证线上已部署环境与本地代码完全同步。

---

## User API

### POST `/users/register`
注册普通账号。

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `username` | string | 是 | 3-20 位，首字符需为字母或下划线，仅允许字母、数字、下划线 |
| `password` | string | 是 | 6-20 位，至少包含 1 个数字 |
| `email` | string | 是 | 注册邮箱 |
| `code` | string | 是 | 通过 `/users/register/email_verify` 获取的邮箱验证码 |
| `phone` | string | 是 | 中国大陆手机号，注册必填 |
| `phone_code` | string | 是 | 通过 `/users/register/phone_verify` 获取的短信验证码 |
| `lang_pref` | `jp \| fr \| private` | 否 | 默认 `private` |
| `portrait` | string | 否 | 默认 `#` |

成功响应：

```json
{
  "id": 1,
  "message": "register success",
  "access_token": "jwt",
  "token_type": "bearer"
}
```

常见错误：
- `400`：邮箱/短信验证码错误或过期、邮箱已注册、手机号已注册、用户名/密码不合法
- `422`：请求体校验失败

---

### POST `/users/register/email_verify`
发送注册验证码。

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `email` | string | 是 | 未注册邮箱 |

成功响应：

```json
{ "message": "验证码已发送" }
```

---

### POST `/users/register/phone_verify`
发送注册短信验证码。

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `phone_number` | string | 是 | 未注册的中国大陆手机号 |

成功响应：

```json
{ "message": "验证码已发送" }
```

---

### POST `/users/login`
用户名密码登录。

请求体：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `name` | string | 是 |
| `password` | string | 是 |

成功响应：

```json
{
  "access_token": "jwt",
  "refresh_token": "jwt",
  "token_type": "bearer",
  "expires_in": 72000,
  "refresh_expires_in": 2592000,
  "user": {
    "id": 1,
    "username": "alice",
    "is_admin": false,
    "lang_pref": "fr",
    "portrait": "#",
    "login_type": "password"
  },
  "is_new_user": false
}
```

常见错误：
- `404`：用户不存在
- `400`：用户名或密码错误

---

### POST `/users/refresh`
刷新会话，返回新的 access/refresh token 对。

请求体：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `refresh_token` | string | 是 |

成功响应结构与 `/users/login` 一致。

常见错误：
- `401`：`refresh token 已过期`、`无效的 refresh token`、`refresh token 已失效`

---

### GET `/users/me`
获取当前用户信息。
需要登录。

成功响应：

```json
{
  "id": 1,
  "username": "alice",
  "is_admin": false,
  "lang_pref": "fr",
  "portrait": "#",
  "login_type": "password"
}
```

---

### POST `/users/logout`
退出登录。
需要登录。

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `refresh_token` | string | 否 | 若传入，则同时废弃该 refresh 会话 |

成功响应：

```json
{ "message": "logout ok" }
```

---

### PUT `/users/update`
修改当前用户资料。
需要登录。

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `current_password` | string | 是 | 当前密码 |
| `new_username` | string | 否 | 新用户名 |
| `new_password` | string | 否 | 新密码 |
| `new_language` | `jp \| fr \| private` | 否 | 新语言偏好 |

成功响应：

```json
{
  "message": "用户信息更新成功",
  "user": {
    "id": 1,
    "username": "alice",
    "is_admin": false,
    "lang_pref": "fr",
    "portrait": "#",
    "login_type": null
  }
}
```

常见错误：
- `400`：缺少当前密码、原密码错误、用户名冲突、密码不合法

---

### POST `/users/auth/forget-password/email`
发送邮箱找回密码验证码。

请求体：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `email` | string | 是 |

成功响应：

```json
{ "message": "验证码已发送" }
```

常见错误：
- `404`：用户不存在

---

### POST `/users/auth/varify_code/email`
验证邮箱验证码，换取重置密码令牌。

请求体：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `email` | string | 是 |
| `code` | string | 是 |

成功响应：

```json
{ "reset_token": "token" }
```

---

### POST `/users/auth/reset-password`
使用 `x-reset-token` 重置密码。

Header：

| 字段 | 必填 | 说明 |
|---|---:|---|
| `x-reset-token` | 是 | 由 `/users/auth/varify_code/email` 返回 |

请求体：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `password` | string | 是 |

成功响应：

```json
{ "message": "密码重置成功" }
```

---

### GET `/users/auth/wechat/login`
发起网页微信扫码登录。

成功行为：
- `307`：重定向到微信授权页

常见错误：
- `500`：微信配置缺失

---

### GET `/users/auth/wechat/callback`
网页微信扫码回调。

Query：

| 参数 | 类型 | 必填 |
|---|---|---:|
| `code` | string | 是 |
| `state` | string | 是 |

成功行为：
- 若微信已绑定站内账号：返回与 `/users/login` 相同结构的登录结果
- 若微信尚未绑定站内账号：返回

```json
{
  "status": "need_phone",
  "bind_ticket": "ticket",
  "login_type": "wechat_open",
  "message": "该微信尚未绑定站内账号，请先完成手机号短信验证，系统将自动匹配或创建账号",
  "wechat_profile": {
    "nickname": "xxx"
  }
}
```

- 若配置了前端回跳地址：`307` 重定向回前端；已绑定时附带 `token`，未绑定时附带 `status=need_phone` 和 `bind_ticket`

---

### POST `/users/auth/wechat/bind/start`
已登录用户发起网页微信绑定。

需要登录。

成功响应：

```json
{
  "authorize_url": "https://open.weixin.qq.com/...",
  "message": "请跳转到微信授权页完成绑定"
}
```

说明：
- 前端拿到 `authorize_url` 后跳转即可。
- 绑定完成后，微信会回调 `/users/auth/wechat/callback`。
- 若配置了 `WECHAT_CALLBACK_SUCCESS_URL`，回跳时会附带 `status=bound`。

---

### POST `/users/auth/wechat/bind/existing`
将一个尚未绑定的微信身份绑定到已有账号。

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `bind_ticket` | string | 是 | 来自未绑定微信登录返回 |
| `username` | string | 是 | 原有站内账号用户名 |
| `password` | string | 是 | 原有站内账号密码 |

成功响应：
- 返回与 `/users/login` 相同结构的登录结果

常见错误：
- `400`：`bind_ticket` 无效或过期、用户名或密码错误
- `404`：用户不存在
- `409`：该微信已绑定其他用户，或当前账号已绑定其他微信身份

---

### POST `/users/auth/wechat/phone_verify`
给微信登录流程发送短信验证码。

Query：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `bind_ticket` | string | 是 | 来自微信登录未绑定返回 |

请求体：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `phone_number` | string | 是 |

成功响应：

```json
{ "message": "验证码已发送" }
```

说明：
- 该接口不会区分手机号是否已注册。
- 后续在 `/users/auth/wechat/complete_by_phone` 中由系统自动判断：
  已有账号则绑定并登录；没有账号则自动创建新账号并绑定微信。

---

### POST `/users/auth/wechat/complete_by_phone`
通过手机号短信验证码完成微信登录。

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `bind_ticket` | string | 是 | 来自微信登录未绑定返回 |
| `phone_number` | string | 是 | 中国大陆手机号 |
| `code` | string | 是 | 通过 `/users/auth/wechat/phone_verify` 获取的短信验证码 |

成功行为：
- 若手机号已对应站内账号：绑定该微信并返回登录结果
- 若手机号尚未注册：自动创建一个新账号，绑定微信并返回登录结果，返回中的 `is_new_user=true`

说明：
- 自动创建的新账号会生成系统用户名、随机密码哈希和占位邮箱，后续可在资料页补全。

---

### POST `/users/auth/wechat/mini/login`
微信小程序登录。

请求体：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `code` | string | 是 |

成功行为：
- 若微信已绑定站内账号：返回与 `/users/login` 相同结构的登录结果，`user.login_type` 为 `wechat_miniapp`
- 若当前请求已携带站内登录态，且该微信尚未绑定：会直接绑定到当前登录账号，然后返回新的登录结果
- 若微信尚未绑定且当前未登录：返回 `status=need_phone + bind_ticket`

---

### POST `/users/auth/wechat/app/login`
移动应用端微信登录。

请求体：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `code` | string | 是 |

成功行为：
- 若微信已绑定站内账号：返回与 `/users/login` 相同结构的登录结果，`user.login_type` 为 `wechat_app`
- 若当前请求已携带站内登录态，且该微信尚未绑定：会直接绑定到当前登录账号，然后返回新的登录结果
- 若微信尚未绑定且当前未登录：返回 `status=need_phone + bind_ticket`

说明：
- 网页版、miniapp、移动应用端共用同一套后端判定逻辑：
  已绑定直接登录，未绑定返回 `bind_ticket`，已登录态下可直接绑定当前账号
- 若用户未登录且微信未绑定，统一先走手机号短信验证：
  有老账号则按手机号匹配并绑定，没有老账号则自动创建新账号并绑定

---

### Deprecated
以下接口已标记弃用，且当前实现存在兼容性风险，不建议继续接入：

#### POST `/users/auth/forget-password/phone`
手机找回密码入口，代码仍挂载但实现使用了旧字段，当前不建议使用。

#### POST `/users/auth/varify_code`
手机验证码校验接口，代码仍挂载但依赖旧实现，当前不建议使用。

---

## Culture Share API

### GET `/culture_share/banners`
公开接口。获取首页轮播。

Query：

| 参数 | 类型 | 必填 | 默认值 |
|---|---|---:|---|
| `limit` | int | 否 | `4` |

成功响应：

```json
{
  "article_cnt": 4,
  "article_list": [
    {
      "id": 1,
      "title": "标题",
      "subtitle": "副标题",
      "image_url": "/media/xx.png",
      "target_url": "/culture_share/article/xxx",
      "sort_order": 0,
      "is_active": true,
      "start_at": null,
      "end_at": null
    }
  ]
}
```

---

### GET `/culture_share/article/list`
公开接口。获取已发布文章分页列表。

Query：

| 参数 | 类型 | 必填 | 默认值 |
|---|---|---:|---|
| `page` | int | 否 | `1` |
| `page_size` | int | 否 | `10` |
| `category` | string | 否 | - |
| `keyword` | string | 否 | - |

成功响应：

```json
{
  "page": 1,
  "page_size": 10,
  "total": 12,
  "items": [
    {
      "article_id": "art_xxx",
      "title": "标题",
      "summary": "摘要",
      "source": "LEXIVERSE",
      "cover_url": "/media/cover.png",
      "category": "culture",
      "tags": ["tag1", "tag2"],
      "publish_at": "2026-04-21T12:00:00",
      "created_at": "2026-04-20T12:00:00"
    }
  ]
}
```

---

### GET `/culture_share/article/{article_id}`
文章详情。

权限规则：
- 匿名用户：只能查看已发布文章
- 管理员：可预览未发布文章

成功响应：

```json
{
  "article_id": "art_xxx",
  "title": "标题",
  "summary": "摘要",
  "source": "LEXIVERSE",
  "cover_url": "/media/cover.png",
  "content_html": "<p>...</p>",
  "content_text": "纯文本内容",
  "category": "culture",
  "tags": ["tag1"],
  "publish_at": "2026-04-21T12:00:00",
  "created_at": "2026-04-20T12:00:00",
  "updated_at": "2026-04-21T12:00:00"
}
```

常见错误：
- `404`：文章不存在或未发布

---

### GET `/culture_share/tags`
公开接口。获取高频标签。

Query：

| 参数 | 类型 | 必填 | 默认值 |
|---|---|---:|---|
| `limit` | int | 否 | `10` |

成功响应：

```json
{
  "total": 10,
  "items": [
    {
      "tag_id": "tag_xxx",
      "name": "文化",
      "usage_count": 8
    }
  ]
}
```

---

## Search API

### POST `/search/word`
公开接口。精确查词。

请求体：

| 字段 | 类型 | 必填 | 默认值 |
|---|---|---:|---|
| `query` | string | 是 | - |
| `language` | `fr \| jp` | 是 | - |
| `sort` | `relevance \| date` | 否 | `date` |
| `order` | `asc \| des` | 否 | `des` |

成功响应：

```json
{
  "query": "bonjour",
  "pos": ["n.", "v."],
  "contents": [
    {
      "pos": "n.",
      "chi_exp": "中文释义",
      "eng_explanation": "english explanation",
      "example": "example"
    }
  ],
  "hiragana": null
}
```

说明：
- 法语返回 `contents[].pos / chi_exp / eng_explanation / example`
- 日语返回 `contents[].chi_exp / example`，并可能带 `hiragana`

---

### POST `/search/list/word`
公开接口。查词联想。

请求体同 `/search/word`。

成功响应：

```json
{
  "list": []
}
```

`list` 中元素来自服务层合并结果，实际可能是字符串、数组或对象，前端需做兼容解析。

---

### POST `/search/list/proverb`
公开接口。法语谚语联想。

请求体：

| 字段 | 类型 | 必填 | 默认值 |
|---|---|---:|---|
| `query` | string | 是 | - |
| `dict_language` | `fr \| jp` | 否 | `fr` |

成功响应：

```json
{
  "list": [
    {
      "id": 1,
      "proverb": "Petit à petit...",
      "chi_exp": "中文释义"
    }
  ]
}
```

---

### POST `/search/proverb`
公开接口。谚语详情。

请求体：`application/x-www-form-urlencoded`

| 字段 | 类型 | 必填 |
|---|---|---:|
| `proverb_id` | int | 是 |

成功响应：

```json
{
  "result": {
    "id": 1,
    "text": "谚语原文",
    "chi_exp": "中文释义"
  }
}
```

---

### POST `/search/list/idiom`
公开接口。日语惯用句联想。

请求体：

| 字段 | 类型 | 必填 | 默认值 |
|---|---|---:|---|
| `query` | string | 是 | - |
| `dict_language` | `fr \| jp` | 否 | `fr` |

成功响应：

```json
{
  "list": [
    {
      "id": 1,
      "text": "原文",
      "search_text": "かな",
      "chi_exp": "中文释义"
    }
  ]
}
```

---

### POST `/search/idiom`
公开接口。日语惯用句详情。

请求参数：
- `query_id`：通过 Query 传入整数 ID

成功响应：

```json
{
  "result": {
    "id": 1,
    "text": "原文",
    "search_text": "かな",
    "chi_exp": "中文释义",
    "example": "例句"
  }
}
```

---

## Translation API

### POST `/translate`
翻译接口。
需要登录。
每用户当前有简单限流：约 `1 秒内最多 2 次请求`。

请求体：

| 字段 | 类型 | 必填 | 默认值 |
|---|---|---:|---|
| `query` | string | 是 | - |
| `from_lang` | `auto \| fra \| jp \| zh \| en` | 否 | `auto` |
| `to_lang` | `fra \| jp \| zh \| en` | 是 | - |

成功响应：

```json
{ "translated_text": "翻译结果" }
```

常见错误：
- `400`：百度翻译返回错误、参数不合法
- `401`：未登录
- `429`：限流触发

---

### POST `/translate/debug`
管理员调试翻译接口。
需要管理员权限。

参数通过 Query 传入：

| 参数 | 类型 | 必填 | 默认值 |
|---|---|---:|---|
| `query` | string | 是 | - |
| `from_lang` | string | 否 | `auto` |
| `to_lang` | string | 否 | `zh` |

成功响应与 `/translate` 相同。

---

## AI Assist API

### POST `/ai_assist/word/exp`
词语 AI 问答。
需要登录。

请求体：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `word` | string | 是 |
| `question` | string | 是 |

成功响应：

```json
{
  "word": "bonjour",
  "answer": "解释内容",
  "model": "deepseek-r1-671b",
  "tokens_used": 123
}
```

常见错误：
- `400`：本月 API 使用量已超
- `500`：上游 AI 服务异常

---

### POST `/ai_assist/clear`
清除指定词语的 AI 聊天记录。
需要登录。

兼容两种传参方式：
- JSON Body：`{"word": "bonjour"}`
- Query：`?word=bonjour`

成功响应：

```json
{ "msg": "已清除 bonjour 的聊天记录" }
```

---

### POST `/ai_assist/univer`
占位接口。
当前实现为空，返回值不稳定，不建议接入。

---

## Article Director API

### POST `/article-director/article`
作文批改。
需要登录。

Query：

| 参数 | 类型 | 必填 | 默认值 |
|---|---|---:|---|
| `lang` | `en-US \| fr-FR \| ja-JP` | 否 | `fr-FR` |

请求体：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `theme` | string | 否 |
| `content` | string | 是 |
| `article_type` | string | 是 |

成功响应：

```json
{
  "reply": "批改结果",
  "tokens": 512,
  "conversation_length": 2
}
```

---

### POST `/article-director/question`
作文追问。
需要登录。

请求体：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `query` | string | 是 |

成功响应结构与 `/article-director/article` 一致。

---

### POST `/article-director/reset`
重置作文上下文。
需要登录。

成功响应：

```json
{ "message": "已重置用户 1 的作文对话记录" }
```

---

## Pronunciation Test API

以下接口全部需要登录。

### GET `/test/pron/start`
开始或恢复发音测评。

Query：

| 参数 | 类型 | 必填 | 默认值 |
|---|---|---:|---|
| `count` | int | 否 | `20` |
| `lang` | `fr-FR \| ja-JP` | 否 | `fr-FR` |

成功响应：

```json
{
  "ok": true,
  "resumed": false,
  "message": "New fr-FR test started",
  "session": {
    "lang": "fr-FR",
    "current_index": 0,
    "sentence_ids": [1, 2, 3],
    "total": 3
  }
}
```

---

### POST `/test/pron/sentence_test`
上传单句录音并打分。

请求体：`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `record` | file | 是 | 仅支持 `.wav` |
| `lang` | `fr-FR \| ja-JP` | 是 | 必须与当前 session 语言一致 |

成功响应：

```json
{
  "ok": true,
  "data": {
    "ok": true,
    "overall_score": 90,
    "accuracy": 88,
    "fluency": 91,
    "completeness": 92,
    "recognized_text": "text",
    "progress": "1/5"
  }
}
```

---

### GET `/test/pron/current_sentence`
获取当前待测句子。

成功响应：

```json
{
  "ok": true,
  "index": 0,
  "current_sentence": "句子文本",
  "total": 5
}
```

若无会话：

```json
{ "ok": false, "error": "No active test session" }
```

---

### POST `/test/pron/testlist`
获取当前测试会话中的题目列表。

成功响应：

```json
[
  { "id": 1, "text": "句子 1" },
  { "id": 2, "text": "句子 2" }
]
```

---

### POST `/test/pron/finish`
结束测评。

请求体：`application/x-www-form-urlencoded`

| 字段 | 类型 | 必填 | 默认值 |
|---|---|---:|---|
| `confirm` | bool | 否 | `false` |

成功返回分三类：
- 未完成且 `confirm=false`：返回 `ok=false, unfinished=true`
- 未完成且 `confirm=true`：返回 `ok=true, forced_end=true, data=部分结果`
- 已完成：返回 `ok=true, data=完整结果`

---

### POST `/test/pron/clear_session`
清空当前 Redis 中的发音测试会话。

成功响应：

```json
{
  "ok": true,
  "message": "Session cleared"
}
```

---

## Comment API

### POST `/improvements`
提交用户反馈。
需要登录。

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `report_part` | string | 是 | 允许值：`ui_design`、`dict_fr`、`dict_jp`、`user`、`translate`、`writting`、`ai_assist`、`pronounce` |
| `text` | string | 是 | 反馈内容 |

成功响应：

```json
{ "massages": "feedback succeed" }
```

---

## Public Info API

### GET `/about-us`
获取“关于应用”展示所需的公开信息。
无需登录。

成功响应：

```json
{
  "app_name": "Lexiverse",
  "version": "2.1",
  "description": "面向小语种学习者的词典与学习平台，提供法语/日语查词、文化阅读、AI 辅助、翻译与发音测评能力。",
  "website": "https://lexiverse.com.cn",
  "team": "Lexiverse 团队"
}
```

注意：
- 返回字段名当前实现是 `massages`，不是 `message`。

---

## Word Comment API

### POST `/comment/word/{lang}`
提交词条评论。
需要登录。

Path 参数：

| 参数 | 类型 | 必填 |
|---|---|---:|
| `lang` | `fr \| jp` | 是 |

请求体：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `comment_word` | string | 是 |
| `comment_content` | string | 是 |

当前实现成功后未显式返回内容，HTTP 200 响应体通常为 `null`。

---

## Admin Article API

以下接口全部需要管理员权限，统一前缀为 `/admin/article`。

### POST `/admin/article/create_article`
创建文章。

### PUT `/admin/article/{article_id}`
更新文章。

### POST `/admin/article/{article_id}/publish`
发布文章。

### POST `/admin/article/{article_id}/unpublish`
撤回为草稿。

### DELETE `/admin/article/{article_id}`
删除文章。

### GET `/admin/article/{article_id}`
获取文章详情。

### GET `/admin/article/{article_id}/published`
查询发布状态。

### GET `/admin/article/{article_id}/banner`
查询轮播状态。

### GET `/admin/article`
文章列表。

Query：

| 参数 | 类型 | 必填 |
|---|---|---:|
| `page` | int | 否 |
| `page_size` | int | 否 |
| `status` | string | 否 |
| `category` | string | 否 |
| `keyword` | string | 否 |

### POST `/admin/article/{article_id}/cover/upload`
上传封面图。`multipart/form-data`，字段名 `file`。

### POST `/admin/article/upload-temp-images`
临时上传正文图片。`multipart/form-data`，字段名 `files`，支持多图。

### DELETE `/admin/article/upload-temp-images`
删除临时图片。

请求体：

```json
{
  "image_urls": ["url1", "url2"]
}
```

### POST `/admin/article/{article_id}/content-images/upload`
上传正文图片。`multipart/form-data`，字段名 `files`。

### GET `/admin/article/tag/search`
搜索标签。

Query：

| 参数 | 类型 | 必填 | 默认值 |
|---|---|---:|---|
| `keyword` | string | 否 | - |
| `limit` | int | 否 | `20` |

### POST `/admin/article/tag`
创建标签。

请求体：

```json
{ "name": "文化" }
```

### POST `/admin/article/{article_id}/banner/switch`
开关文章轮播状态。

请求体字段：
- `enabled`
- `title`
- `subtitle`
- `image_url`
- `target_url`
- `sort_order`
- `start_at`
- `end_at`

所有管理员文章接口的详细响应字段，请以
[admin_articles_schemas.py](/Users/godrictan/Desktop/ECNU/双创/小语种词典/dict_server/app/api/admin/admin_articles/admin_articles_schemas.py)
为准。

---

## Miniapp API

### GET `/miniapp/home`
公开接口。返回小程序首页聚合数据。

成功响应：

```json
{
  "banners": [],
  "hot_tags": [],
  "featured_articles": [],
  "quick_entries": [
    {
      "key": "search",
      "title": "词汇查询",
      "subtitle": "查找单词、近义词与语境解释",
      "target_page": "/pages/search/index"
    }
  ]
}
```

---

## Utility / Test API

### GET `/ping-redis`
公开测试接口。返回 Redis 连通信息。

### GET `/search_time`
公开接口。读取累计搜索次数。

成功响应：

```json
{ "count": 123 }
```

### GET `/search/reset`
公开接口。重置累计搜索次数。

成功响应：

```json
{ "message": "search times reset successfully" }
```
