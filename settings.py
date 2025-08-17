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


class Settings(BaseSettings):
    USE_OAUTH = False
    SECRET_KEY = "asdasdasd-odjfnsodfnosidnfdf-0oq2j01j0jf0i1ej0fij10fd"


settings = Settings()
