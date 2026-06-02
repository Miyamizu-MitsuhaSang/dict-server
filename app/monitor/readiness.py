"""
服务健康检查与就绪检查。

health 更偏向“进程是否活着”；readiness 更偏向“依赖是否可用，是否能对外提供服务”。
这里检查 Redis 和数据库，方便部署平台或开发者快速判断服务状态。
"""

from typing import Any

from starlette.requests import Request
from tortoise import Tortoise


async def check_redis(request: Request) -> dict[str, Any]:
    """
    检查 FastAPI app.state.redis 是否可用。

    Redis 在 main.py 的 lifespan 中初始化，所以这里从 request.app.state 读取。
    """
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        return {"ok": False, "detail": "redis client is not initialized"}

    try:
        await redis.ping()
    except Exception as exc:
        return {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}

    return {"ok": True}


async def check_database() -> dict[str, Any]:
    """
    检查默认数据库连接是否可用。

    Tortoise ORM 已经在 main.py 中注册，这里执行一条轻量 SELECT 1。
    如果数据库不可用，会返回失败原因，但不会让检查接口直接崩掉。
    """
    try:
        connection = Tortoise.get_connection("default")
        await connection.execute_query("SELECT 1")
    except Exception as exc:
        return {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}

    return {"ok": True}


async def build_readiness_report(request: Request) -> dict[str, Any]:
    """
    汇总所有依赖检查结果。

    所有依赖都 ok 时，服务才算 ready。
    """
    checks = {
        "redis": await check_redis(request),
        "database": await check_database(),
    }
    ready = all(item["ok"] for item in checks.values())
    return {"ok": ready, "checks": checks}
