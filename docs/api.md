# FastAPI  
版本：0.1.0

**认证方式**  
部分接口需要 `OAuth2PasswordBearer`，在 Header 中添加：  

```http
Authorization: Bearer <token>
```

------

## User API

### Register
**Method**: `POST`  
**Path**: `/users/register`

#### 请求体
| 字段     | 类型   | 必填 | 说明 |
|----------|--------|------|------|
| username | string | 是   | Username |
| password | string | 是   | Password |
| lang_pref | string(enum: jp, fr, private，默认: private) | 否 | Lang Pref |
| portrait | string(默认: #) | 否 | Portrait |

#### 响应
**200 成功**  
| 字段   | 类型   | 必填 | 说明 |
|--------|--------|------|------|
| name   | string | 是   | Name |
| potrait| string(默认: #) | 否 | Potrait |

**422 验证错误**  
返回 `HTTPValidationError`

---

### User Modification
**Method**: `PUT`  
**Path**: `/users/update`  
需要认证

描述：根据 JSON 内容修改对应字段。

#### 请求体
| 字段             | 类型   | 必填 | 说明 |
|------------------|--------|------|------|
| current_password | string / null | 否 | Current Password |
| new_username     | string / null | 否 | New Username |
| new_password     | string / null | 否 | New Password |
| new_language     | string(enum: jp, fr, private，默认: private) | 否 | New Language |

#### 响应
- **200 成功**（空 schema）  
- **422 验证错误**

------

### User Logout

**Method**: `POST`
 **Path**: `/users/logout`
 需要认证

#### 响应

- **200 成功**（空 schema）

------

## Dictionary Search API

### Search

**Method**: `POST`
 **Path**: `/search`
 需要认证

#### 请求体

| 字段     | 类型                                      | 必填 | 说明     |
| -------- | ----------------------------------------- | ---- | -------- |
| query    | string                                    | 是   | Query    |
| language | string(enum: fr, jp)                      | 是   | Language |
| sort     | string(enum: relevance, date，默认: date) | 否   | Sort     |
| order    | string(enum: asc, des，默认: des)         | 否   | Order    |

#### 响应

**200 成功**

| 字段     | 类型                                    | 必填 | 说明     |
| -------- | --------------------------------------- | ---- | -------- |
| query    | string                                  | 是   | Query    |
| pos      | array                                   | 是   | Pos      |
| contents | array(SearchItemFr[] 或 SearchItemJp[]) | 是   | Contents |

**422 验证错误**

### Search List

**Method**: `POST`
 **Path**: `search/list`
 需要认证

描述：检索提示接口，根据用户输入返回候选列表。

#### 请求体

同 `/search`

#### 响应

- **200 成功**（空 schema）
- **422 验证错误**

------

## Redis Test-Only API

### Ping Redis

**Method**: `GET`
 **Path**: `/ping-redis`

#### 响应

- **200 成功**

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

