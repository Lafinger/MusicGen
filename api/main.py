from loguru_settings import TraceID, logger, setup_logging
from controller import MusicController

from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, AsyncGenerator
import asyncio
import json
import argparse

# 全局变量
global_semaphore = asyncio.Semaphore(1)
music_controller = MusicController()
app = FastAPI(
        title="音乐生成服务", 
        description="使用Websocket和Streamable HTTP方案实现的音乐生成服务API",
        version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，如["https://example.com", "https://app.example.com"]
    allow_credentials=True, # 允许跨域请求携带凭据（Cookie、认证头、TLS客户端证书）
    allow_methods=["*"],  # 允许所有方法， 如：["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    allow_headers=["*"],  # 允许所有请求头， 如：["Content-Type", "Authorization", "X-Request-Id"]
    expose_headers=["*"],  # 暴露所有请求头， 如：["Content-Type", "Authorization", "X-Request-Id"]
    max_age=600, # 预检请求（OPTIONS）结果的缓存时间（秒）, 减少OPTIONS请求频率，提高性能
)

@app.middleware("http")
async def request_middleware(request: Request, call_next) -> Response:
    """
    1.设置日志的全链路追踪
    2.记录错误日志
    """
    try:
        REQUEST_ID_KEY = "X-Request-Id"
        _req_id_val = request.headers.get(REQUEST_ID_KEY, "??????") # 如果请求头中没有X-Request-Id，则设置为??????
        req_id = TraceID.set(_req_id_val)
        logger.info(f"{request.method} {request.url}")
        response = await call_next(request)
        response.headers[REQUEST_ID_KEY] = req_id.get()
        return response
    except Exception as ex:
        logger.exception(ex)  # 这个方法能记录错误栈
        return JSONResponse(content={"success": False}, status_code=500)
    finally:
        pass


async def generate_progress_stream(data: Dict, request: Request) -> AsyncGenerator[str, None]:
    """生成进度流"""
    generation_task = None  # 初始化为None，防止在异常时未定义
    try:
        stop_event = asyncio.Event()
        progress_event = asyncio.Event()
        progress_value: float = 0.0
        
        # 创建一个进度回调函数
        def progress_callback(percentage: float):
            if stop_event.is_set():
                logger.info("Stop progress callback")
                raise InterruptedError("Stop event is set, stop progress callback")
            nonlocal progress_value
            progress_value = percentage
            progress_event.set()

        # 发送开始事件
        logger.info("Sending start event")
        yield f"data: {json.dumps({'event': 'start'})}\n\n"

        # 启动音乐生成任务
        logger.info("Start music generation task")

        generation_task = asyncio.create_task(asyncio.to_thread(
            music_controller.generate_music_with_progress,
            params=data,
            progress_callback=progress_callback
        ))
    
        # 处理进度消息直到生成完成
        while not generation_task.done() and not generation_task.cancelled() and progress_value < 100:
            await asyncio.wait(
                [progress_event.wait(), generation_task],  # 等待进度事件或任务完成
                return_when=asyncio.FIRST_COMPLETED,
                timeout=1
            )
            progress_event.clear()
            logger.info("Send progress message")
            yield f"data: {json.dumps({'event': 'progress', 'progress': progress_value})}\n\n"

        # 如果任务没有被取消，获取生成结果并发送
        if not generation_task.cancelled():
            audio_data = await generation_task
            yield f"data: {json.dumps({'event': 'completed', 'audio': audio_data})}\n\n"

    except AssertionError as e:
        logger.exception(e)
        yield f"data: {json.dumps({'event': 'error', 'message': '音乐生成参数错误'})}\n\n"
    except asyncio.CancelledError as e:
        progress_event.set()
        stop_event.set()
        logger.error("client cancel connection")
    finally:
        if generation_task is not None and not generation_task.done():
            generation_task.cancel()
        global_semaphore.release()
        logger.info("Semaphore released after generate progress stream completion")

@app.post("/api/v1/generate_music")
async def http_generate_music(request: Request) -> Response:
    """流式生成音乐接口
    """
    # 限流检测
    if global_semaphore.locked():
        return JSONResponse(
            status_code=503,
            content={"error": "服务器正忙，当前正在处理任务，请稍后重试"}
        )
    else:
        await global_semaphore.acquire()
    
        # 获取请求数据
        try:
            data = await request.json()
        except Exception:
            global_semaphore.release()
            return JSONResponse(
                status_code=400,
                content={"error": "入参出错，请检查入参是否为json格式"}
            )
        
        # 返回SSE流式响应
        return StreamingResponse(
            generate_progress_stream(data, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache", # 禁止浏览器缓存响应内容， 用于SSE流式响应
                "Connection": "keep-alive", # 保持连接， 用于SSE流式响应
                "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲， Nginx默认会缓冲响应再发送，导致流式数据延迟，禁用后，Nginx会立即发送响应
                "Access-Control-Allow-Origin": "*"  # 允许跨域访问
            }
        )


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="音乐生成服务API")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="服务监听地址，默认为0.0.0.0")
    parser.add_argument("--port", type=int, default=5555, help="服务监听端口，默认为5555")
    parser.add_argument("--music_model_name", type=str, default="facebook/musicgen-large", help="音乐生成模型名称，默认为facebook/musicgen-large")
    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()

    # 解析命令行参数
    args = parse_arguments()
    
    # 初始化音乐大模型
    music_controller.init_music_model(args.music_model_name)

    import uvicorn
    uvicorn.run("main:app", host=args.host, port=args.port, log_config="uvicorn_config.json", log_level="info")
