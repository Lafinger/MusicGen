from loguru_settings import TraceID, logger, setup_logging
from controller import MusicController

from fastapi import FastAPI, Request, Header
from fastapi.responses import Response, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import AsyncGenerator, Optional, Dict, Any, Literal, Union
import asyncio
import json
import argparse
import uuid

# 全局变量
global_semaphore = asyncio.Semaphore(1)
music_controller = MusicController()
app = FastAPI(
    title="音乐生成服务", 
    description="使用Streamable HTTP方案实现的音乐生成服务API",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc"
)

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

# 定义请求体
class MusicGenerationRequest(BaseModel):
    description: str = Field(..., description="用于音乐生成的文本提示")
    mbd: Optional[bool] = Field(default=False, description="是否使用多波段扩散模型")
    duration: Optional[int] = Field(default=30, description="生成音乐的时长(秒)", ge=1, le=60)
    top_k: Optional[int] = Field(default=250, description="采样时考虑的最高概率的标记数", gt=0)
    top_p: Optional[float] = Field(default=0.0, description="采样时考虑的累积概率阈值", ge=0, le=1)
    temperature: Optional[float] = Field(default=3.0, description="采样温度，控制随机性", ge=0)
    cfg_coef: Optional[float] = Field(default=3.0, description="无分类器指导系数")

# 定义响应体
# 定义API响应示例
SUCCESS_RESPONSE_EXAMPLE = {
    "description": "成功响应，返回事件流",
    "content": {
        "text/event-stream": {
            "example": 'data: {"event": "start"}\n\n'
                      'data: {"event": "progress", "progress": 50.0}\n\n'
                      'data: {"event": "completed", "audio": "base64_audio_data..."}'
        }
    }
}

VALIDATION_ERROR_RESPONSE_EXAMPLE = {
    "description": "验证错误",
    "content": {
        "application/json": {
            "example": {"detail": [{"loc": ["body", "description"], "msg": "field required", "type": "value_error.missing"}]}
        }
    }
}

SERVER_BUSY_RESPONSE_EXAMPLE = {
    "description": "服务器忙",
    "content": {
        "application/json": {
            "example": {"error": "服务器正忙，当前正在处理任务，请稍后重试"}
        }
    }
}

# 组合所有响应
API_RESPONSES_EXAMPLE: Dict[Union[int, str], Dict[str, Any]] = {
    200: SUCCESS_RESPONSE_EXAMPLE,
    422: VALIDATION_ERROR_RESPONSE_EXAMPLE,
    503: SERVER_BUSY_RESPONSE_EXAMPLE
}

class EventStreamResponse(BaseModel):
    event: Literal["start", "progress", "completed", "error"] = Field(..., description="事件类型")
    progress: Optional[float] = Field(default=None, description="生成进度百分比", ge=0, le=100)
    audio: Optional[str] = Field(default=None, description="Base64编码的音频数据")
    message: Optional[str] = Field(default=None, description="错误信息")

class ServerBusyResponse(BaseModel):
    """服务器忙响应模型"""
    error: str = Field(..., description="错误信息")


async def generate_progress_stream(data: Dict[str, Any], request: Request) -> AsyncGenerator[str, None]:
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
        start_event = EventStreamResponse(event="start")
        yield f"data: {json.dumps(start_event.model_dump(exclude_none=True))}\n\n"

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
            progress_event_data = EventStreamResponse(event="progress", progress=progress_value)
            yield f"data: {json.dumps(progress_event_data.model_dump(exclude_none=True))}\n\n"

        # 如果任务没有被取消，获取生成结果并发送
        if not generation_task.cancelled():
            audio_data = await generation_task
            completed_event = EventStreamResponse(event="completed", audio=audio_data)
            yield f"data: {json.dumps(completed_event.model_dump(exclude_none=True))}\n\n"

    except AssertionError as e:
        logger.exception(e)
        error_event = EventStreamResponse(event="error", message="音乐生成参数错误")
        yield f"data: {json.dumps(error_event.model_dump(exclude_none=True))}\n\n"
    except asyncio.CancelledError as e:
        progress_event.set()
        stop_event.set()
        logger.error("client cancel connection")
    finally:
        if generation_task is not None and not generation_task.done():
            generation_task.cancel()
        global_semaphore.release()
        logger.info("Semaphore released after generate progress stream completion")

@app.post(
    "/api/v1/generate_music", 
    summary="Http Generate Music", 
    description="使用Streamable HTTP流式响应生成音乐接口",
    response_class=StreamingResponse,
    responses=API_RESPONSES_EXAMPLE
)
async def http_generate_music(
    request: Request, 
    music_params: MusicGenerationRequest,
    content_type: str = Header("application/json", description="必须为application/json", alias="Content-Type"),
    accept: str = Header("text/event-stream", description="必须为text/event-stream", alias="Accept"),
    x_request_id: str = Header(uuid.uuid4(), description="UUID4全链路追踪", alias="X-Request-Id"),
) -> Response:
    """使用Streamable HTTP流式响应生成音乐接口
    
    Args:
        music_params: 音乐生成的参数
        content_type: 内容类型，必须为application/json
        accept: 接收类型，必须为text/event-stream
        x_request_id: 请求追踪ID，用于全链路追踪
        
    Returns:
        流式事件响应，包含进度和最终生成的音频数据
    """
    # 限流检测
    if global_semaphore.locked():
        busy_response = ServerBusyResponse(error="服务器正忙，当前正在处理任务，请稍后重试")
        return JSONResponse(
            status_code=503,
            content=busy_response.model_dump()
        )
    else:
        await global_semaphore.acquire()
        
        # 将Pydantic模型转换为字典
        params = music_params.model_dump()
        
        # 返回SSE流式响应
        return StreamingResponse(
            generate_progress_stream(params, request),
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
