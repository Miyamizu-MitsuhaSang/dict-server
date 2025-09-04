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

- **接口**: `POST /users/register`
- **描述**: 新用户注册
- **请求体**:

```json
{
  "username": "string",
  "password": "string", 
  "lang_pref": "jp" | "fr" | "private",
  "portrait": "string"
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

---

### 2. 词典搜索模块

#### 2.1 词典搜索

- **接口**: `POST /search`
- **描述**: 根据关键词搜索词典内容
- **需要认证**: 是
- **请求体**:

```json
{
  "query": "string",
  "language": "fr" | "jp",
  "sort": "relevance" | "date",
  "order": "asc" | "des"
}
```

- **法语响应示例**:

```json
{
  "query": "string",
  "pos": ["n.m.", "v.t."],
  "contents": [
    {
      "pos": "n.m.",
      "chi_exp": "中文解释",
      "eng_explanation": "English explanation", 
      "example": "例句"
    }
  ]
}
```

- **日语响应示例**:

```json
{
  "query": "string", 
  "pos": ["名词", "动词"],
  "contents": [
    {
      "chi_exp": "中文解释",
      "example": "例句"
    }
  ]
}
```

- **状态码**:
  - `200`: 搜索成功
  - `404`: 未找到词条
  - `401`: 未授权

#### 2.2 搜索建议

- **接口**: `POST /search/list`
- **描述**: 获取搜索自动完成建议
- **需要认证**: 是
- **请求体**:

```json
{
  "query": "string",
  "language": "fr" | "jp"
}
```

---

### 3. 管理员模块 (`/admin`)

> **注意**: 所有管理员接口都需要管理员权限

#### 3.1 获取词典列表

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

#### 3.2 搜索词条

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

---

### 4. 数据模型

#### 4.1 法语词性枚举

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

#### 4.2 日语词性枚举

```text
名词, 形容词, 形容动词, 连用, 一段动词, 五段动词, 
助词, 自动词, 他动词, 接尾, 自他动词, 接续, 
惯用, 感叹词, カ変, サ変, 连体, 量词, 代词
```

---

### 5. 错误码说明

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未授权/令牌无效 |
| 403 | 权限不足 |
| 404 | 资源未找到 |
| 500 | 服务器内部错误 |

---

### 6. 使用示例

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
curl -X POST "http://127.0.0.1:8000/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token_here>" \
  -d '{
    "query": "bonjour",
    "language": "fr"
  }'
```

---

### 7. 开发者说明

- **数据库**: 使用MySQL存储词典数据和用户信息
- **缓存**: 使用Redis进行token黑名单管理
- **认证**: JWT令牌有效期为2小时
- **CORS**: 支持本地开发环境跨域访问
- **API文档**: 启动服务后访问 `http://127.0.0.1:8000/docs` 查看Swagger文档

---

### 8. 部署说明

1. 安装依赖: `pip install -r requirements.txt`
2. 配置数据库连接 (settings.py)
3. 启动Redis服务
4. 运行数据库迁移
5. 启动服务: `python main.py`

---

*文档版本: 1.0*  
*最后更新: 2025年9月4日*
