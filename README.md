# 词典服务器 API 接口文档

## 项目概述

本项目是一个多语言词典API服务，支持法语和日语词典的查询和管理功能。基于FastAPI框架开发，提供用户认证、词典搜索、后台管理等功能。

**服务器地址**: `http://127.0.0.1:8000`  
**技术栈**: FastAPI, Tortoise ORM, MySQL, Redis, JWT

---

## 认证说明

大部分API需要JWT令牌认证。在请求头中包含：

```http
Authorization: Bearer <your_jwt_token>
```

---

## API 接口分类

### 1. 用户认证模块 (`/users`)

#### 1.1 用户注册
##### 1.1.1 注册主接口

- **接口**: `POST /users/register`
- **描述**: 新用户注册
- **请求体**:

```json
{
  "username": "string",
  "password": "string", 
  "email": "EmailFields[string]",
  "phone": "PhoneFields",
  "lang_pref": "jp" | "fr" | "private",
  "portrait": "string",
  "code": "string"
}
```

- **响应**:

```json
{
  "id": "integer",
  "message": "register success"
}
```

- **状态码**:
  - `200`: 注册成功
  - `400`: 参数验证失败

##### 1.1.2 邮箱验证

- **接口**: `POST /users/register/email_verify`
- **描述**: 新用户注册时的邮箱验证
- **请求体**:

```json
{
  "email" : "string"
}
```

- **响应**:

```json
{
  "message": "验证码已发送"
}
```

- **状态码**:
  - `200`: 邮件发送成功
  - `400`: 邮箱已被使用

#### 1.2 用户登录

- **接口**: `POST /users/login`
- **描述**: 用户登录获取访问令牌
- **请求体**:

```json
{
  "name": "string",
  "password": "string"
}
```

- **响应**:

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "user": {
    "id": "integer",
    "username": "string", 
    "is_admin": "boolean"
  }
}
```

- **状态码**:
  - `200`: 登录成功
  - `400`: 用户名或密码错误
  - `404`: 用户不存在

#### 1.3 用户登出

- **接口**: `POST /users/logout`
- **描述**: 用户登出，将令牌加入黑名单
- **需要认证**: 是
- **响应**:

```json
{
  "message": "logout ok"
}
```

- **状态码**:
  - `200`: 登出成功
  - `401`: 未登录或令牌无效

#### 1.4 更新用户信息

- **接口**: `PUT /users/update`
- **描述**: 修改用户信息（用户名、密码等）
- **需要认证**: 是
- **请求体**:

```json
{
  "current_password": "string",
  "new_username": "string",
  "new_password": "string",
  "new_language": "jp" | "fr" | "private"
}
```

- **状态码**:
  - `200`: 更新成功
  - `400`: 原密码错误或用户名为保留词

#### 1.5 邮箱找回密码（发送验证码）

- **接口**: `POST /users/auth/forget-password/email`  
- **描述**: 用户请求通过邮箱找回密码时，向注册邮箱发送验证码  
- **请求体**:

```json
{
  "email": "string"
}
```


- **响应**:

```json
{
  "message": "验证码已发送"
}
```


- **状态码**
  - `200`: 更新成功
  - `404`: 用户不存在

#### 1.6 邮箱验证码验证

- **接口**: `POST /users/auth/varify_code/email`  
- **描述**: 用户输入邮箱验证码后，验证验证码是否有效，返回重置令牌  
- **请求体**:
```json
{
  "email": "string",
  "code": "string"
}
```

- **响应**
```json
{
  "reset_token": "string"
}
```

- **状态码**
  - `200`: 验证码验证成功
  - `400`: 验证码错误或已过期

#### 1.7 重置密码

- **接口**: `POST /users/auth/reset-password`  
- **描述**: 用户通过邮箱验证码获得的重置令牌来设置新密码 
- **请求头**: 
  - `x-reset-token`: 重置令牌
- **请求体**:
```json
{
  "password": "string"
}
```

- **响应**
```json
{
  "massage": "密码重置成功"
}
```

- **状态码**
  - `200`: 密码重置成功
  - `400`: 密码不合法或令牌无效

#### 1.8 手机找回密码（已废弃）

> **说明**: 该接口仍在服务端保留，但已不再推荐使用，后续版本可能会移除。

- **接口**: `POST /users/auth/forget-password/phone`
- **描述**: 通过手机号码请求验证码以找回密码
- **请求体**:

```json
{
  "phone_number": "string"
}
```

- **响应**:

```json
{
  "message": "验证码已发送"
}
```

- **状态码**:
  - `200`: 发送成功
  - `404`: 手机号未注册

#### 1.9 手机验证码验证（已废弃）

> **说明**: 该接口与 1.8 配合使用，已不再推荐使用。

- **接口**: `POST /users/auth/varify_code`
- **描述**: 校验短信验证码是否有效
- **请求体**:

```json
{
  "phone": "string",
  "code": "string"
}
```

- **响应**:

```json
{
  "message": "验证成功，可以重置密码"
}
```

- **状态码**:
  - `200`: 验证成功
  - `400`: 验证码错误或已过期

---

### 2. 词典搜索模块 (`Dictionary Search API`)

#### 2.1 单词精确搜索

- **接口**: `POST /search/word`
- **描述**: 根据语言精确查询词条，自动累计词频并返回按词性分组的释义。
- **需要认证**: 是
- **请求体**:

```json
{
  "query": "bonjour",
  "language": "fr",
  "sort": "relevance",
  "order": "des"
}
```

- **法语响应示例** (`language = fr`):

```json
{
  "query": "bonjour",
  "pos": ["n.m."],
  "contents": [
    {
      "pos": "n.m.",
      "chi_exp": "问候语；用于见面时打招呼",
      "eng_explanation": "greeting; hello",
      "example": "Bonjour, comment ça va ?"
    }
  ]
}
```

- **日语响应示例** (`language = jp`):

```json
{
  "query": "日本語",
  "pos": ["名词"],
  "contents": [
    {
      "chi_exp": "日语；日本的语言",
      "example": "日本語を勉強しています。"
    }
  ]
}
```

- **状态码**:
  - `200`: 搜索成功
  - `404`: 未找到词条
  - `401`: 未授权

#### 2.2 法语谚语详情

- **接口**: `POST /search/proverb`
- **描述**: 根据谚语ID返回法语谚语全文与中文释义。
- **需要认证**: 是
- **请求类型**: `application/x-www-form-urlencoded`
- **表单字段**:
  - `proverb_id`: 谚语ID (integer，必填)
- **响应**:

```json
{
  "result": {
    "text": "Petit à petit, l'oiseau fait son nid.",
    "chi_exp": "循序渐进才能取得成功。",
    "freq": 128
  }
}
```

- **状态码**:
  - `200`: 查询成功
  - `404`: 谚语不存在

#### 2.3 单词联想建议

- **接口**: `POST /search/list/word`
- **描述**: 根据用户输入返回单词联想列表，含前缀匹配与包含匹配。
- **需要认证**: 是
- **请求体**:

```json
{
  "query": "bon",
  "language": "fr",
  "sort": "relevance",
  "order": "des"
}
```

- **响应示例**:

```json
{
  "list": ["bonjour", "bonsoir", "bonheur"]
}
```

> **说明**: `language = "jp"` 时返回形如 `[["愛", "あい"], ["愛する", "あいする"]]` 的二维数组，第二列为假名读音。

- **状态码**:
  - `200`: 查询成功

#### 2.4 谚语联想建议

- **接口**: `POST /search/list/proverb`
- **描述**: 按输入内容返回谚语候选列表，后端会自动检测输入语言（中文/日文假名/拉丁字母），无法识别时退回法语字段搜索。
- **需要认证**: 是
- **请求体**:

```json
{
  "query": "慢",
  "dict_language": "fr"
}
```

- **响应示例**:

```json
{
  "list": [
    {
      "id": 12,
      "proverb": "Rien ne sert de courir, il faut partir à point.",
      "chi_exp": "做事要循序渐进，贵在及时出发。"
    }
  ]
}
```

- **状态码**:
  - `200`: 查询成功

#### 2.5 日语惯用语联想建议

- **接口**: `POST /search/list/idiom`
- **描述**: 针对日语惯用语返回联想候选，支持输入日文假名或中文汉字；若输入匹配汉字映射表，会并发查询假名结果并合并输出。
- **需要认证**: 是
- **请求体**:

```json
{
  "query": "愛してる",
  "dict_language": "jp"
}
```

- **响应示例**:

```json
{
  "list": [
    {
      "id": 21,
      "proverb": "愛してる",
      "chi_exp": "我爱你"
    }
  ]
}
```

- **状态码**:
  - `200`: 查询成功
  - `400`: 当 `dict_language` 不是 `jp` 时返回错误信息

#### 2.6 日语惯用语详情

- **接口**: `POST /search/idiom`
- **描述**: 根据惯用语 ID 返回详细信息并增加访问频次。
- **需要认证**: 是
- **查询参数**:
  - `query_id`: 惯用语 ID (integer)
- **响应示例**:

```json
{
  "result": {
    "id": 21,
    "text": "愛してる",
    "search_text": "あいしてる",
    "chi_exp": "我爱你",
    "example": "私はあなたを愛してる。",
    "freq": 57
  }
}
```

- **状态码**:
  - `200`: 查询成功
  - `404`: 惯用语不存在

---

### 3. 翻译模块 (`/translate`)

#### 3.1 文本翻译

- **接口**: `POST /translate`
- **描述**: 使用百度翻译API进行文本翻译
- **需要认证**: 是
- **请求体**:

```json
{
  "query": "Hello World",
  "from_lang": "auto",
  "to_lang": "zh"
}
```

- **请求参数说明**:
  - `query`: 待翻译的文本
  - `from_lang`: 源语言，支持值: `auto`(自动检测), `fr`(法语), `jp`(日语), `zh`(中文)，默认为 `auto`
  - `to_lang`: 目标语言，支持值: `fr`(法语), `jp`(日语), `zh`(中文)，默认为 `zh`，不能为 `auto`

- **响应**:

```json
{
  "translated_text": "你好世界"
}
```

- **限制**: 依赖 Redis 计数器做限流，同一用户每秒最多 2 次请求（超出返回 `429`）
- **状态码**:
  - `200`: 翻译成功
  - `401`: 未授权
  - `500`: 翻译服务错误

#### 3.2 调试翻译接口

- **接口**: `POST /translate/debug`
- **描述**: 管理员专用的翻译调试接口，带有限流保护
- **需要认证**: 管理员权限
- **查询参数**:
  - `query`: 待翻译文本
  - `from_lang`: 源语言，默认为 `auto`
  - `to_lang`: 目标语言，默认为 `zh`

- **限制**: 与标准翻译接口共享限流计数，同一用户每秒最多2次请求
- **状态码**:
  - `200`: 翻译成功
  - `429`: 请求频率过高
  - `403`: 权限不足

---

### 4. Redis测试模块 (`/ping-redis`)

#### 4.1 Redis连接测试

- **接口**: `GET /ping-redis`
- **描述**: 测试Redis连接状态
- **需要认证**: 否
- **响应**:

```json
{
  "pong": true,
  "redis": {
    "host": "127.0.0.1",
    "port": 6379,
    "db": 0
  }
}
```

---

### 5. 管理员模块 (`/admin`)

> **注意**: 所有管理员接口都需要管理员权限

#### 5.1 获取词典列表

- **接口**: `GET /admin/dict`
- **描述**: 分页获取词典数据，用于后台管理
- **需要认证**: 管理员权限
- **查询参数**:
  - `page`: 页码 (默认: 1, 最小: 1)
  - `page_size`: 每页条数 (默认: 10, 最大: 10)
  - `lang_code`: 语言代码 ("fr" | "jp", 默认: "fr")

- **响应**:

```json
{
  "total": "integer",
  "data": [
    {
      "word__text": "string",
      "pos": "string", 
      "meaning": "string",
      "example": "string",
      "eng_explanation": "string"
    }
  ]
}
```

#### 5.2 搜索词条

- **接口**: `POST /admin/dict/search_word`
- **描述**: 在后台管理中搜索特定词条
- **需要认证**: 管理员权限
- **请求体**:

```json
{
  "word": "string",
  "language": "fr" | "jp",
  "pos": "string"
}
```

- **响应**:

```json
[
  {
    "id": "integer",
    "word": "string",
    "pos": "string",
    "meaning": "string", 
    "example": "string",
    "eng_explanation": "string"
  }
]
```

#### 5.3 批量更新词条

- **接口**: `PUT /admin/dict/adjust`
- **描述**: 批量更新词典定义内容
- **需要认证**: 管理员权限
- **请求体**:

```json
{
  "updates": [
    {
      "id": "integer",
      "language": "fr" | "jp",
      "pos": "string",
      "meaning": "string",
      "example": "string",
      "eng_explanation": "string"
    }
  ]
}
```

- **响应**:

```json
{
  "success_count": "integer",
  "errors": ["string"]
}
```

- **状态码**:
  - `200`: 更新成功
  - `400`: 词条不存在
  - `422`: 无改动信息

#### 5.4 添加新词条

- **接口**: `POST /admin/dict/add`
- **描述**: 添加新的词典条目
- **需要认证**: 管理员权限
- **请求体**:

```json
{
  "word": "string",
  "language": "fr" | "jp",
  "pos": "string",
  "meaning": "string",
  "example": "string",
  "eng_explanation": "string"
}
```

- **状态码**:
  - `200`: 添加成功
  - `409`: 释义已存在
  - `400`: 不支持的语言类型

#### 5.5 Excel批量导入

- **接口**: `POST /admin/dict/update_by_xlsx`
- **描述**: 通过Excel文件批量导入词典数据
- **需要认证**: 管理员权限
- **请求类型**: `multipart/form-data`
- **请求参数**:
  - `file`: Excel文件 (.xlsx 或 .xls 格式)

- **响应**:

```json
{
  "message": "导入成功"
}
```

- **状态码**:
  - `200`: 导入成功
  - `400`: 文件格式错误
  - `500`: 导入失败

---

### 6. 用户反馈模块 (`/improvements`)

#### 6.1 提交用户反馈

- **接口**: `POST /improvements`
- **描述**: 登录用户提交产品改进或问题反馈，系统会向预设邮箱发送通知。
- **需要认证**: 是
- **请求体**:

```json
{
  "report_part": "string",
  "text": "string"
}
```

- **字段说明**:
  - `report_part`: 反馈类别，可选值 `ui_design`, `dict_fr`, `dict_jp`, `user`, `translate`, `writting`, `ai_assist`, `pronounce`（`comment_api_test` 仅用于内部测试）
  - `text`: 反馈正文，不能为空

- **响应**:

```json
{
  "massages": "feedback succeed"
}
```

- **状态码**:
  - `200`: 提交成功
  - `422`: 字段校验失败（不合法的类别或空文本）

---

### 7. 词条评论模块 (`/comment/word`)

#### 7.1 新增词条评论

- **接口**: `POST /comment/word/{lang}`
- **描述**: 为指定语言的词条添加用户评论
- **需要认证**: 是
- **路径参数**:
  - `lang`: `fr` 或 `jp`
- **请求体**:

```json
{
  "comment_word": "string",
  "comment_content": "string"
}
```

- **响应**: 创建成功时返回 `200`，响应体为空。
- **状态码**:
  - `200`: 创建成功
  - `422`: 字段校验失败

---

### 8. 作文指导模块 (`/article-director`)

#### 8.1 作文批改会话

- **接口**: `POST /article-director/article`
- **描述**: 将学生作文（文本形式）提交给 EduChat 模型获取结构化点评，会话上下文保存在 Redis 中。
- **需要认证**: 是
- **查询参数**:
  - `lang`: 作文语种，默认 `fr-FR`，可选值 `fr-FR`（法语）、`ja-JP`（日语）、`en-US`（英文）
- **请求体**:

```json
{
  "title_content": "我的作文全文......",
  "article_type": "议论文"
}
```

- **响应**:

```json
{
  "reply": "整体点评内容……",
  "tokens": 1834,
  "conversation_length": 3
}
```

- **状态码**:
  - `200`: 批改成功
  - `401`: 未授权

> **提示**: 每次调用批改/追问接口之后，前端应根据需要调用重置接口清空 Redis 中的上下文。

#### 8.2 作文追问

- **接口**: `POST /article-director/question`
- **描述**: 在现有作文会话上追加提问，获取针对性回复。
- **需要认证**: 是
- **请求体**:

```json
{
  "query": "请给出第三段的改写示例"
}
```

- **响应**:

```json
{
  "reply": "改写建议……",
  "tokens": 924,
  "conversation_length": 5
}
```

- **状态码**:
  - `200`: 追问成功
  - `401`: 未授权

#### 8.3 重置作文会话

- **接口**: `POST /article-director/reset`
- **描述**: 清除当前用户在 Redis 中的作文指导上下文，确保下一次批改从头开始。
- **需要认证**: 是
- **响应**:

```json
{
  "message": "已重置用户 <user_id> 的作文对话记录"
}
```

---

### 9. 发音测评模块 (`/test/pron`)

#### 9.1 开始/恢复测评

- **接口**: `GET /test/pron/start`
- **描述**: 为当前用户新建或恢复发音测评会话，默认随机抽取20句目标语言的测评文本。
- **需要认证**: 是
- **查询参数**:
  - `count`: 抽题数量 (integer，默认 `20`)
- **表单字段**:
  - `lang`: 语种代码（`fr-FR` 或 `ja-JP`，默认 `fr-FR`）。由于实现方式，FastAPI 将其视为 form-data 字段，GET 请求需通过 form 提交或在调试文档中直接填写。
- **响应**:

```json
{
  "ok": true,
  "resumed": false,
  "message": "New fr-FR test started",
  "session": {
    "lang": "fr-FR",
    "current_index": 0,
    "sentence_ids": [12, 45, 87],
    "total": 3
  }
}
```

- **状态码**:
  - `200`: 成功创建或恢复会话
  - `400`: 不支持的语言参数
  - `404`: 题库为空

#### 9.2 提交语音测评

- **接口**: `POST /test/pron/sentence_test`
- **描述**: 上传 `.wav` 录音进行发音测评，服务端自动转换格式并调用 Azure Speech 评分。
- **需要认证**: 是
- **请求类型**: `multipart/form-data`
- **表单字段**:
  - `record`: 上传的音频文件（仅支持 `.wav`）
  - `lang`: 语种代码，默认 `fr-FR`
- **响应示例**:

```json
{
  "ok": true,
  "data": {
    "ok": true,
    "recognized_text": "Bonjour tout le monde",
    "overall_score": 84.5,
    "accuracy": 82.0,
    "fluency": 86.0,
    "completeness": 85.0,
    "progress": "3/10"
  }
}
```

- **状态码**:
  - `200`: 评分成功（若全部句子完成，会自动结束会话）
  - `400`: 会话不存在或音频转换失败
  - `404`: 对应题目不存在
  - `415`: 音频格式不符合要求

#### 9.3 查询当前题目

- **接口**: `GET /test/pron/current_sentence`
- **描述**: 返回当前需要朗读的句子。
- **需要认证**: 是
- **响应**:

```json
{
  "ok": true,
  "index": 2,
  "current_sentence": "Bonjour tout le monde"
}
```

- **状态码**:
  - `200`: 查询成功
  - `404`: 会话不存在

#### 9.4 查看本次题目列表

- **接口**: `POST /test/pron/testlist`
- **描述**: 返回本次测评抽取的所有句子列表及其 ID。
- **需要认证**: 是
- **响应示例**:

```json
[
  {"id": 12, "text": "Bonjour tout le monde"},
  {"id": 45, "text": "Je m'appelle Léa"}
]
```

- **状态码**:
  - `200`: 查询成功
  - `404`: 会话不存在

#### 9.5 结束测评

- **接口**: `POST /test/pron/finish`
- **描述**: 结束当前测评会话，并返回成绩。若测评未完成，需要携带 `confirm=true` 强制结束。
- **需要认证**: 是
- **请求体**: `application/x-www-form-urlencoded`
  - `confirm`: boolean，默认 `false`
- **响应示例（强制结束）**:

```json
{
  "ok": true,
  "forced_end": true,
  "message": "⚠️ Test forcefully ended. 3/10 sentences completed.",
  "data": {
    "ok": true,
    "average_score": 82.3,
    "records": [
      {
        "sentence_id": 12,
        "overall_score": 84.5
      }
    ]
  }
}
```

- **状态码**:
  - `200`: 成功结束会话
  - `404`: 会话或结果不存在

#### 9.6 清除测评会话

- **接口**: `POST /test/pron/clear_session`
- **描述**: 主动清除 Redis 中的测评会话（用户放弃测评时使用）。
- **需要认证**: 是
- **响应**:

```json
{
  "ok": true,
  "message": "Session cleared"
}
```

---

### 10. 数据模型

#### 10.1 法语词性枚举

```text
n. - 名词
n.f. - 阴性名词  
n.m. - 阳性名词
v. - 动词
v.t. - 及物动词
v.i. - 不及物动词
adj. - 形容词
adv. - 副词
prep. - 介词
pron. - 代词
conj. - 连词
interj. - 感叹词
art. - 冠词
```

#### 10.2 日语词性枚举

```text
名词, 形容词, 形容动词, 连用, 一段动词, 五段动词, 
助词, 自动词, 他动词, 接尾, 自他动词, 接续, 
惯用, 感叹词, カ変, サ変, 连体, 量词, 代词
```

---

### 11. 错误码说明

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未授权/令牌无效 |
| 403 | 权限不足 |
| 404 | 资源未找到 |
| 409 | 资源冲突（如重复数据） |
| 422 | 请求实体错误 |
| 429 | 请求频率过高 |
| 500 | 服务器内部错误 |

---

### 12. AI助手模块 (`/ai_assist`)

#### 12.1 词语智能问答

- **接口**: `POST /ai_assist/word/exp`
- **描述**: 针对指定词语向AI助手提问，服务端会基于Redis保存的上下文历史给出简洁、贴合学习者的回答。
- **需要认证**: 是（`Bearer` Token）
- **请求体**:

```json
{
  "word": "string",
  "question": "string"
}
```

- **限制**:
  - 普通用户调用次数超过100次时会返回 `400 本月API使用量已超`
  - 每个 `word` 独立维护聊天上下文，历史保存于Redis

- **响应**:

```json
{
  "word": "string",
  "answer": "string",
  "model": "string",
  "tokens_used": "integer"
}
```

- **状态码**:
  - `200`: 问答成功
  - `400`: 本月API使用量已超
  - `401`: 未授权
  - `500`: AI调用失败

#### 12.2 通用AI对话（预留）

- **接口**: `POST /ai_assist/univer`
- **描述**: 预留的通用AI对话接口，当前版本尚未实现业务逻辑，调用将返回空响应。
- **需要认证**: 是
- **状态码**:
  - `200`: 请求成功（响应体为空）

#### 12.3 清除词语聊天记录

- **接口**: `POST /ai_assist/clear`
- **描述**: 清除指定词语的AI助手聊天记录
- **需要认证**: 是
- **请求参数**:
  - `word`: 词语 (query 参数，string)

- **响应**:

```json
{
  "msg": "已清除 <word> 的聊天记录"
}
```

- **状态码**:
  - `200`: 清除成功

---

### 13. 使用示例

#### 完整的API调用流程示例

```bash
# 1. 用户注册
curl -X POST "http://127.0.0.1:8000/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123",
    "lang_pref": "fr"
  }'

# 2. 用户登录
curl -X POST "http://127.0.0.1:8000/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "testuser", 
    "password": "password123"
  }'

# 3. 使用返回的token进行词典搜索
curl -X POST "http://127.0.0.1:8000/search/word" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token_here>" \
  -d '{
    "query": "bonjour",
    "language": "fr",
    "sort": "relevance",
    "order": "des"
  }'

# 4. 获取单词联想列表
curl -X POST "http://127.0.0.1:8000/search/list/word" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token_here>" \
  -d '{
    "query": "bon",
    "language": "fr"
  }'

# 5. 使用翻译API
curl -X POST "http://127.0.0.1:8000/translate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token_here>" \
  -d '{
    "query": "Hello World",
    "from_lang": "auto",
    "to_lang": "zh"
  }'

# 6. 测试Redis连接
curl -X GET "http://127.0.0.1:8000/ping-redis"

# 7. 词语智能问答
curl -X POST "http://127.0.0.1:8000/ai_assist/word/exp" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token_here>" \
  -d '{
    "word": "法语",
    "question": "什么是法语?"
  }'

# 8. 清除词语聊天记录
curl -X POST "http://127.0.0.1:8000/ai_assist/clear?word=法语" \
  -H "Authorization: Bearer <your_token_here>"

# 9. 开启发音测评
curl -X GET "http://127.0.0.1:8000/test/pron/start?count=5&lang=fr-FR" \
  -H "Authorization: Bearer <your_token_here>"
```

---

### 14. 开发者说明

- **数据库**: 使用MySQL存储词典数据和用户信息
- **缓存**: 使用Redis进行token黑名单管理和API限流
- **认证**: JWT令牌有效期为2小时
- **翻译服务**: 集成百度翻译API，支持多语言互译
- **限流保护**: 翻译调试接口有每秒2次请求限制
- **文件上传**: 支持Excel格式的批量词典导入
- **CORS**: 支持本地开发环境跨域访问
- **API文档**: 启动服务后访问 `http://127.0.0.1:8000/docs` 查看Swagger文档
- **发音评测**: `/test/pron` 路由已预留，当前版本尚未提供具体接口

---

### 15. 部署说明

1. 安装依赖: `pip install -r requirements.txt`
2. 配置数据库连接 (settings.py)
3. 配置百度翻译API密钥 (BAIDU_APPID, BAIDU_APPKEY)
4. 启动Redis服务
5. 运行数据库迁移
6. 启动服务: `python main.py`

---

*文档版本: 2.0*  
*最后更新: 2025年9月22日*
