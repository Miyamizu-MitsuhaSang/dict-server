"""
监控查看接口。

这些接口不记录业务数据，只返回服务状态和访问统计，便于开发、联调和部署检查。
"""

from fastapi import APIRouter, Depends, Request
from starlette.responses import JSONResponse

from app.monitor.metrics import request_metrics
from app.monitor.readiness import build_readiness_report
from app.utils.security import is_admin_user


monitor_router = APIRouter()


@monitor_router.get("/health")
async def health_check():
    """
    存活检查。

    只要服务进程能正常响应，就返回 ok。
    """
    return {"ok": True}


@monitor_router.get("/readiness")
async def readiness_check(request: Request):
    """
    就绪检查。

    会检查 Redis、数据库等依赖是否可用。
    """
    report = await build_readiness_report(request)
    status_code = 200 if report["ok"] else 503
    return JSONResponse(report, status_code=status_code)


@monitor_router.get("/metrics", dependencies=[Depends(is_admin_user)])
async def metrics_snapshot():
    """
    返回接口访问统计快照。

    数据来自 metrics.py 中的内存计数器。
    这个接口包含访问量、路径统计等运维信息，所以限制为管理员访问。
    """
    return request_metrics.snapshot()
