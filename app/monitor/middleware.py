"""
接口访问监控模块。

这个模块通过 FastAPI 的 HTTP middleware 拦截每一次接口访问，
在请求完成后统一打印访问记录，并把访问数据交给 metrics 模块做统计。
"""

import json
import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from jose import JWTError, jwt
from starlette.requests import Request

from app.monitor.logging_filter import sanitize_query_string
from app.monitor.metrics import request_metrics


logger = logging.getLogger("monitor.access")


def _setup_logger() -> None:
    """
    初始化访问日志打印器。

    这里使用标准库 logging，并把日志直接输出到控制台。
    如果 logger 已经绑定过 handler，就直接返回，避免开发环境 reload 后重复打印。
    """
    if logger.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def _get_client_ip(request: Request) -> str:
    """
    获取真实客户端 IP。

    线上服务通常会经过 Nginx、负载均衡或网关代理，真实 IP 会被放在
    X-Forwarded-For 或 X-Real-IP 请求头中；如果没有代理头，再退回到
    request.client.host。
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # X-Forwarded-For 可能是多个 IP，第一个一般是最初的客户端 IP。
        return forwarded_for.split(",", 1)[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    if request.client:
        return request.client.host
    return "unknown"


def _get_user_id(request: Request) -> Any:
    """
    从 Bearer Token 中读取 user_id。

    这里只做未校验解析，用于打印访问轨迹，不参与鉴权逻辑。
    真正的接口权限仍然由 app/utils/security.py 中的依赖负责校验。
    """
    auth = request.headers.get("Authorization", "")
    parts = auth.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    try:
        claims = jwt.get_unverified_claims(parts[1])
    except JWTError:
        return None
    return claims.get("user_id")


def _get_request_id(request: Request) -> str:
    """
    获取或生成请求 ID。

    如果上游网关已经传入 X-Request-ID，就沿用它，方便串联网关日志和后端日志；
    如果没有，就生成一个 UUID，保证每条访问日志都有可追踪标识。
    """
    request_id = request.headers.get("x-request-id")
    if request_id:
        return request_id.strip()
    return str(uuid4())


def _build_access_record(
        request: Request,
        *,
        started_at: str,
        status_code: int,
        duration_ms: float,
        request_id: str,
        error: str | None = None,
) -> dict[str, Any]:
    """
    组装一条接口访问记录。

    记录内容包含请求 ID、方法、路径、状态码、耗时、客户端 IP、User-Agent 和用户 ID。
    出于安全考虑，不打印请求体、密码、手机号、Authorization Token 等敏感数据。
    """
    record = {
        "event": "api_access",
        "time": started_at,
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "client_ip": _get_client_ip(request),
        "user_agent": request.headers.get("user-agent", ""),
        "user_id": _get_user_id(request),
    }

    if request.url.query:
        # query 一般用于排查筛选条件；打印前先交给 logging_filter 做敏感字段脱敏。
        record["query"] = sanitize_query_string(request.url.query)
    if error:
        record["error_type"] = error

    return record


def register_monitor(app: FastAPI) -> None:
    """
    注册接口访问监控中间件。

    main.py 调用一次这个函数即可让整个 FastAPI 应用具备访问记录能力。
    middleware 会包裹所有 HTTP 请求，等接口处理完成后再统一打印日志。
    """
    _setup_logger()

    @app.middleware("http")
    async def access_monitor(request: Request, call_next):
        """
        实际执行访问监控的 HTTP middleware。

        处理流程：
        1. 请求进入时记录开始时间；
        2. 调用后续 middleware 和业务接口；
        3. 正常响应时记录真实状态码；
        4. 接口抛异常时保留异常信息并继续抛出，避免影响 FastAPI 原有错误处理；
        5. 给响应写入 X-Request-ID，方便前端或网关定位同一次请求；
        6. finally 中统一打印访问记录并更新 metrics，保证成功和失败请求都会被记录。
        """
        start = perf_counter()
        started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        request_id = _get_request_id(request)
        status_code = 500
        error = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            error = type(exc).__name__
            raise
        finally:
            duration_ms = (perf_counter() - start) * 1000
            request_metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            record = _build_access_record(
                request,
                started_at=started_at,
                status_code=status_code,
                duration_ms=duration_ms,
                request_id=request_id,
                error=error,
            )
            logger.info(json.dumps(record, ensure_ascii=False))
