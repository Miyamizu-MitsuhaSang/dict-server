TORTOISE_ORM = {
    'connections': {
        'default': {
            # 'engine': 'tortoise.backends.asyncpg',  PostgreSQL
            'engine': 'tortoise.backends.mysql',  # MySQL or Mariadb
            'credentials': {
                'host': '127.0.0.1',
                'port': '3306',
                'user': 'root',
                'password': 'enterprise',
                'database': 'dict',
                'minsize': 1,
                'maxsize': 5,
                'charset': 'utf8mb4',
                "echo": True
            }
        },
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

SECRET_KEY = "asdasdasd-odjfnsodfnosidnfdf-0oq2j01j0jf0i1ej0fij10fd"
