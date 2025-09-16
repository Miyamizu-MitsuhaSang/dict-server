from pydantic.v1 import BaseSettings

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

    class Config:
        env_file = '.env'


settings = Settings()
