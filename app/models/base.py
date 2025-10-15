"""
后续如果需要修改数据库 key 名字的，需要在 migrate 文件生成后手动修改 SQL 指令
    e.g.
        org: ALTER TABLE "entry" ADD COLUMN "term" VARCHAR(100);
        new: ALTER TABLE "entry" RENAME COLUMN "word" TO "term";
修改完成之后才能进行 upgrade

后续如果要将 Foreign Key 修改为 ManyToMany，需要先保留当前 Key，新建一个，完成迁移后再删除
    e.g.
        entries = await WordEntry.all().prefetch_related("tag")

主机：你的 Tailscale IP（100.x.x.x）
端口：3306
用户名：team_rw
密码：Strong#Passw0rd!
数据库：dict

"""

from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=20, unique=True, description="用户名")
    pwd_hashed = fields.CharField(max_length=60, description="密码")
    portrait = fields.CharField(max_length=120, default='#', description="用户头像")
    email = fields.CharField(max_length=120, description="e-mail")
    encrypted_phone = fields.CharField(max_length=11, description="用户手机号", null=True)
    language = fields.ForeignKeyField("models.Language", related_name="users", on_delete=fields.CASCADE)
    is_admin = fields.BooleanField(default=False, description="管理员权限")
    token_usage = fields.IntField(default=0, description="AI答疑使用量")

    class Meta:
        table = "users"


class ReservedWords(Model):
    id = fields.IntField(pk=True)
    reserved = fields.CharField(max_length=20, description="保留词")
    category = fields.CharField(max_length=20, default="username")

    class Meta:
        table = "reserved_words"


class Language(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=30, unique=True)  # e.g. "Japanese"
    code = fields.CharField(max_length=10, unique=True)  # e.g. "ja", "fr", "zh"
