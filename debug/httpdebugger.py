# 临时加个调试中间件（或异常处理器）
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI
from main import app


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print("422 detail:", exc.errors())  # 在控制台打印
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
