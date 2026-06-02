"""
接口访问指标统计。

这个文件做轻量级内存统计，用来回答：
- 当前服务启动了多久；
- 一共访问了多少次接口；
- 有多少错误请求；
- 各路径、各状态码访问量是多少；
- 平均耗时和最大耗时是多少。

注意：这些数据存在进程内存中，服务重启后会清零；多进程部署时每个进程各算各的。
"""

from collections import Counter
from datetime import datetime
from threading import Lock
from typing import Any


class RequestMetrics:
    """保存并更新接口访问统计数据。"""

    def __init__(self) -> None:
        self.started_at = datetime.now()
        self.total_requests = 0
        self.total_errors = 0
        self.total_duration_ms = 0.0
        self.max_duration_ms = 0.0
        self.path_counter: Counter[str] = Counter()
        self.status_counter: Counter[str] = Counter()
        self.method_counter: Counter[str] = Counter()
        self._lock = Lock()

    def record_request(
            self,
            *,
            method: str,
            path: str,
            status_code: int,
            duration_ms: float,
    ) -> None:
        """
        记录一次接口访问。

        middleware 每处理完一个请求都会调用这里。
        使用 Lock 是为了避免并发请求同时修改 Counter 时出现数据竞争。
        """
        with self._lock:
            self.total_requests += 1
            if status_code >= 400:
                self.total_errors += 1

            self.total_duration_ms += duration_ms
            self.max_duration_ms = max(self.max_duration_ms, duration_ms)
            self.path_counter[path] += 1
            self.status_counter[str(status_code)] += 1
            self.method_counter[method] += 1

    def snapshot(self) -> dict[str, Any]:
        """
        返回当前统计快照。

        routes.py 会把这个结果作为 `/monitor/metrics` 的响应返回。
        """
        with self._lock:
            average_duration_ms = 0.0
            if self.total_requests:
                average_duration_ms = self.total_duration_ms / self.total_requests

            uptime_seconds = (datetime.now() - self.started_at).total_seconds()

            return {
                "started_at": self.started_at.isoformat(timespec="seconds"),
                "uptime_seconds": round(uptime_seconds, 2),
                "total_requests": self.total_requests,
                "total_errors": self.total_errors,
                "average_duration_ms": round(average_duration_ms, 2),
                "max_duration_ms": round(self.max_duration_ms, 2),
                "by_method": dict(self.method_counter),
                "by_status": dict(self.status_counter),
                "by_path": dict(self.path_counter),
            }


# 全局单例：所有请求共享同一份统计数据。
request_metrics = RequestMetrics()
