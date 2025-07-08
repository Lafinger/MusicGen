from controller import MusicController

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, AsyncGenerator, Union, Optional
import asyncio
from loguru import logger
import os
from starlette.websockets import WebSocketState
import json

# 配置日志
log_dir = "./log"
os.makedirs(log_dir, exist_ok=True)

# # 配置 loguru
# logger.add(
#     "./logs/app.log",
#     rotation="50 MB",    # 日志文件达到500MB时轮转
#     retention="1 days",  # 保留10天的日志
#     enqueue=True,        # 异步写入
#     encoding="utf-8",
#     level="INFO",
#     format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
# )

app = FastAPI(
    title="音乐生成服务", 
    description="使用Websocket和Streamable HTTP方案实现的音乐生成服务API",
    version="1.0.0")

router = APIRouter()
music_controller = MusicController()

# 全局信号量，限制只允许一个连接
global_semaphore = asyncio.Semaphore(1)

async def generate_progress_stream(data: dict, request: Request) -> AsyncGenerator[str, None]:
    """生成进度流"""
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

        try:
            # 启动音乐生成任务
            logger.info("Start music generation task")
            generation_task = asyncio.create_task(asyncio.to_thread(
                music_controller.generate_music_with_progress,
                params=data,
                progress_callback=progress_callback
            ))

            # 处理进度消息直到生成完成
            while not generation_task.done() and not generation_task.cancelled() and progress_value < 100:
                try:
                    await asyncio.wait(
                        [progress_event.wait(), generation_task],  # 等待进度事件或任务完成
                        return_when=asyncio.FIRST_COMPLETED,
                        timeout=1
                    )
                    progress_event.clear()
                    logger.info("Send progress message")
                    yield f"data: {json.dumps({'event': 'progress', 'progress': progress_value})}\n\n"
                except Exception as e:
                    logger.error(f"Break loop, error processing progress message: {e}")
                    break

            # 如果任务没有被取消，获取生成结果并发送
            if not generation_task.cancelled():
                try:
                    audio_data = await generation_task
                    yield f"data: {json.dumps({'event': 'completed', 'audio': audio_data})}\n\n"
                except InterruptedError as e:
                    logger.warning(f"Music generation was interrupted: {e}")
                    yield f"data: {json.dumps({'event': 'interrupted', 'message': '音乐生成已被中断'})}\n\n"
                except ValueError as e:
                    logger.error(f"Error in music generated parameters: {str(e)}")
                    yield f"data: {json.dumps({'event': 'error', 'message': f'音乐生成参数错误: {e}'})}\n\n"
                except Exception as e:
                    logger.error(f"Error in getting music generation result: {str(e)}")
                    yield f"data: {json.dumps({'event': 'error', 'message': f'获取音乐生成结果发生错误: {e}'})}\n\n"
        except Exception as e:
            logger.error(f"Error in music generation: {str(e)}")
            yield f"data: {json.dumps({'event': 'error', 'message': f'音乐生成过程中发生错误: {e}'})}\n\n"

    except asyncio.CancelledError:
        if not generation_task.done():
            generation_task.cancel()
        progress_event.set()
        stop_event.set()
        logger.warning("Generate progress stream cancelled")
        yield f"data: {json.dumps({'event': 'cancelled', 'message': '流式生成音乐已取消'})}\n\n"
    except asyncio.TimeoutError:
        logger.error("Generate progress stream timeout")
        yield f"data: {json.dumps({'event': 'error', 'message': '流式生成音乐超时'})}\n\n"
    except Exception as e:
        logger.error(f"Error in progress stream: {e}")
        yield f"data: {json.dumps({'event': 'error', 'message': '音乐生成过程中发生错误'})}\n\n"
    finally:
        generation_task.cancel()
        global_semaphore.release()
        logger.info("Semaphore released after generate progress stream completion")

@router.post("/api/v1/generate_music")
async def http_generate_music(request: Request):
    """流式生成音乐接口
    """
    try:
        # 尝试获取信号量，设置超时时间为0.1秒
        await asyncio.wait_for(global_semaphore.acquire(), timeout=0.1)
        # 获取请求数据
        data = await request.json()
        
        # 查询入参是否为json格式
        if not isinstance(data, dict):
            return JSONResponse(
                status_code=400,
                content={"error": "入参出错，请检查入参是否为json格式"}
            )
      
        # 返回SSE流式响应
        return StreamingResponse(
            generate_progress_stream(data, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
                "Access-Control-Allow-Origin": "*"  # 允许跨域访问
            }
        )

    except asyncio.TimeoutError:
        logger.error("Rate limit reached, request rejected")
        return JSONResponse(
            status_code=503,
            content={"error": "服务器正忙，当前正在处理任务，请稍后重试"}
        )
        
    except Exception as e:
        logger.error(f"Error in server internal: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "服务器内部错误"}
        )

app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5555, log_config="log_config.json", log_level="info")
