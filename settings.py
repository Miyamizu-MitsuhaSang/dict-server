from pathlib import Path

from pydantic.v1 import BaseSettings

# 计算项目根目录：假设 settings.py 位于 dict_server/settings.py
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR  # 如果 settings.py 就在根目录，否则改成 BASE_DIR.parent

TORTOISE_ORM = {
    'connections': {
        "default": "mysql://local_admin:enterprise@127.0.0.1:3306/dict",
        "production": "mysql://local_admin:enterprise@127.0.0.1:3306/prod_db",
    },
    'apps': {
        'models': {
            'models': [
                'app.models.base',
                'app.models.fr',
                'app.models.jp',
                'app.models.comments',
                'aerich.models'  # aerich自带模型类（必须填入）
            ],
            'default_connection': 'default',

        }
    },
    'use_tz': False,
    'timezone': 'Asia/Shanghai'
}

ONLINE_SETTINGS = {
    'connections': {
        'default': 'mysql://root:@127.0.0.1:3306/test_db',
    },
    'apps': {
        'models': {
            'models': [
                'app.models.base',
                'app.models.fr',
                'app.models.jp',
                'app.models.comments',
                'aerich.models'  # aerich自带模型类（必须填入）
            ],
            'default_connection': 'default',

        }
    },
    'use_tz': False,
    'timezone': 'Asia/Shanghai'
}


class Settings(BaseSettings):
    USE_OAUTH: bool = False
    SECRET_KEY: str
    BAIDU_APPID: str
    BAIDU_APPKEY: str
    REDIS_URL: str

    AES_SECRET_KEY: str

    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASS: str
    SMTP_SENDER_NAME: str

    RESET_SECRET_KEY: str

    AI_ASSIST_KEY: str

    ECNU_TEACH_AI_KEY: str

    AZURE_SUBSCRIPTION_KEY: str

    class Config:
        env_file = ROOT_DIR / '.env'
        case_sensitive = False


settings = Settings()
