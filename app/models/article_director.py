from tortoise import fields
from tortoise.models import Model


class ArticleDirectorCallLog(Model):
    id = fields.IntField(pk=True)
    request_id = fields.CharField(max_length=36, unique=True, description="请求追踪ID")
    user = fields.ForeignKeyField("models.User", related_name="article_director_logs", on_delete=fields.CASCADE)
    login_type = fields.CharField(max_length=30, null=True, description="登录方式")

    endpoint = fields.CharField(max_length=120, description="调用接口")
    method = fields.CharField(max_length=10, description="HTTP 方法")
    client_ip = fields.CharField(max_length=64, null=True, description="客户端 IP")
    user_agent = fields.CharField(max_length=512, null=True, description="User-Agent")
    action = fields.CharField(max_length=30, description="写作指导动作")

    lang = fields.CharField(max_length=20, null=True, description="请求语言代码")
    article_lang = fields.CharField(max_length=20, null=True, description="作文语言")
    article_type = fields.CharField(max_length=60, null=True, description="作文体裁")
    theme = fields.CharField(max_length=255, null=True, description="作文标题或主题")

    input_text = fields.TextField(null=True, description="发送给模型的用户输入")
    input_hash = fields.CharField(max_length=64, null=True, description="用户输入 SHA-256")
    input_length = fields.IntField(default=0, description="用户输入长度")
    output_text = fields.TextField(null=True, description="模型回复")
    output_hash = fields.CharField(max_length=64, null=True, description="模型回复 SHA-256")
    output_length = fields.IntField(null=True, description="模型回复长度")

    provider = fields.CharField(max_length=50, default="ECNU EduChat", description="模型服务提供方")
    model = fields.CharField(max_length=50, default="educhat-r1", description="模型名称")
    base_url = fields.CharField(max_length=255, description="模型服务地址")
    temperature = fields.FloatField(null=True, description="temperature 参数")
    top_p = fields.FloatField(null=True, description="top_p 参数")
    system_prompt_hash = fields.CharField(max_length=64, null=True, description="系统提示词 SHA-256")
    message_count = fields.IntField(default=0, description="本次上游消息数量")
    conversation_length_before = fields.IntField(default=0, description="调用前上下文长度")
    conversation_length_after = fields.IntField(null=True, description="调用后上下文长度")
    upstream_request_id = fields.CharField(max_length=120, null=True, description="上游请求或响应 ID")

    prompt_tokens = fields.IntField(null=True, description="输入 token 数")
    completion_tokens = fields.IntField(null=True, description="输出 token 数")
    total_tokens = fields.IntField(null=True, description="总 token 数")
    latency_ms = fields.IntField(null=True, description="上游调用耗时毫秒")
    status = fields.CharField(max_length=20, description="调用状态")
    error_code = fields.CharField(max_length=120, null=True, description="错误类型")
    error_message = fields.TextField(null=True, description="脱敏错误信息")

    risk_flags = fields.JSONField(null=True, description="内容安全与风控标记")
    blocked = fields.BooleanField(default=False, description="是否拦截")
    policy_version = fields.CharField(max_length=50, null=True, description="合规策略版本")
    retention_months = fields.IntField(default=6, description="日志留存月数")
    expires_at = fields.DatetimeField(description="日志到期时间")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        table = "article_director_call_logs"
        indexes = (("user", "created_at"), ("expires_at",), ("status", "created_at"))
