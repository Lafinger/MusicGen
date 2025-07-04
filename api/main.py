from controller import MusicController

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, AsyncGenerator
import asyncio
from loguru import logger
import os
from starlette.websockets import WebSocketState
import json

app = FastAPI(
    title="音乐生成服务", 
    description="使用Websocket和Streamable HTTP方案实现的音乐生成服务API",
    version="1.0.0")

router = APIRouter()

# 配置日志
log_dir = "./logs"
os.makedirs(log_dir, exist_ok=True)

# 全局信号量，限制只允许一个连接
global_semaphore = asyncio.Semaphore(1) 

# 配置 loguru
logger.add(
    "./logs/app.log",
    rotation="50 MB",    # 日志文件达到500MB时轮转
    retention="1 days",  # 保留10天的日志
    enqueue=True,        # 异步写入
    encoding="utf-8",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)



# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        # 存储活跃的WebSocket连接
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        try:
            await websocket.accept()
            self.active_connections[client_id] = websocket
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection for client {client_id}: {e}")
            await websocket.close(code=1006)

    async def disconnect(self, client_id: str):
        try:
            if client_id in self.active_connections:
                ws = self.active_connections[client_id]
                del self.active_connections[client_id]  # 先移除连接
                try:
                    await ws.close(code=1000)  # 使用1000表示正常关闭
                except Exception as e:
                    logger.error(f"Error closing WebSocket for client {client_id}: {e}")
            else:
                logger.error(f"Client {client_id} not found in active connections")
        except Exception as e:
            logger.error(f"Error in disconnect for client {client_id}: {e}")

    async def send_message(self, client_id: str, json_data: Dict):
        try:
            if client_id in self.active_connections:
                if self.active_connections[client_id].client_state == WebSocketState.CONNECTED:
                    await self.active_connections[client_id].send_json(json_data)
                else:
                    logger.error(f"Client {client_id} is not connected")
            else:
                logger.error(f"Client {client_id} not found in active connections")
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")


connection_manager = ConnectionManager()
music_controller = MusicController()

@app.websocket("/ws/generate_music/{client_id}")
async def websocket_generate_music(websocket: WebSocket, client_id: str):
    try:
        # --------------------------------- 限流检测 ---------------------------------
        if not await global_semaphore.acquire():
            try:
                await websocket.accept()
                # 如果无法获取锁，发送忙碌消息并关闭连接
                await websocket.send_json({
                    "event": "error",
                    "message": "服务器正忙，当前正在处理任务，请稍后重试"
                })
            finally:
                await websocket.close(code=1006)
            return

        # ------------------------- 开始处理音乐生成 -------------------------
        try:
            # 将连接添加到管理器
            await connection_manager.connect(websocket, client_id)

            # 创建一个异步的进度回调函数
            async def async_progress_callback(percentage: float):
                json_data = {
                    "event": "generating",
                    "progress": percentage
                }
                await connection_manager.send_message(client_id, json_data)

            # 获取当前事件循环的引用
            loop = asyncio.get_running_loop()
            
            # 创建一个同步的包装器来调用异步回调
            def sync_progress_wrapper(percentage: float):
                future = asyncio.run_coroutine_threadsafe(
                    async_progress_callback(percentage),
                    loop
                )
                future.result(timeout=0.1)

            while True:
                # 等待接收消息
                data = await websocket.receive_json()
                
                # 发送开始事件
                await connection_manager.send_message(client_id, {
                    "event": "start"
                })
                
                # 在单独的线程中运行音乐生成
                audio_data = await asyncio.to_thread(
                    music_controller.generate_music_with_progress,
                    params=data,
                    progress_callback=sync_progress_wrapper
                )

                # 发送完成事件
                await connection_manager.send_message(client_id, {
                    "event": "completed",
                    "audio_data": audio_data
                })
                break

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for client {client_id}")
        except Exception as e:
            logger.error(f"Error in music generation for client {client_id}: {e}")
            try:
                await connection_manager.send_message(client_id, {
                    "event": "error",
                    "message": "音乐生成过程中发生错误"
                })
            except:
                pass

    except Exception as e:
        logger.error(f"Error in WebSocket connection setup for client {client_id}: {e}")
    finally:
        # 确保连接被清理
        await connection_manager.disconnect(client_id)
        # 释放信号量
        global_semaphore.release()
        logger.info(f"WebSocket connection closed for client {client_id}")


async def generate_progress_stream(data: dict) -> AsyncGenerator[str, None]:
    """生成进度流"""
    try:
        # 创建一个事件循环引用
        loop = asyncio.get_running_loop()
        progress_queue = asyncio.Queue()
        
        # 创建一个同步的进度回调函数
        def sync_progress_callback(percentage: float):
            # 将进度放入队列
            asyncio.run_coroutine_threadsafe(
                progress_queue.put({
                    "event": "generating",
                    "progress": percentage
                }),
                loop
            )

        # 发送开始事件
        yield json.dumps({"event": "start"}) + "\n"
        
        # 在单独的线程中运行音乐生成
        audio_task = asyncio.create_task(asyncio.to_thread(
            music_controller.generate_music_with_progress,
            params=data,
            progress_callback=sync_progress_callback
        ))

        # 等待进度更新或音乐生成完成
        while True:
            try:
                # 等待进度队列或音频生成任务
                done, _ = await asyncio.wait(
                    [
                        asyncio.create_task(progress_queue.get()),
                        audio_task
                    ],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # 检查哪个任务完成了
                for task in done:
                    if task == audio_task:
                        # 音频生成完成
                        audio_data = await audio_task
                        # 发送完成事件
                        yield json.dumps({
                            "event": "completed",
                            "audio_data": audio_data
                        }) + "\n"
                        return
                    else:
                        # 进度更新
                        progress_data = task.result()
                        yield json.dumps(progress_data) + "\n"
                        
            except Exception as e:
                # 发送错误事件
                yield json.dumps({
                    "event": "error",
                    "message": f"音乐生成过程中发生错误: {str(e)}"
                }) + "\n"
                return
                
    except Exception as e:
        logger.error(f"Error in progress stream: {e}")
        yield json.dumps({
            "event": "error",
            "message": "音乐生成过程中发生错误"
        }) + "\n"

@router.post("/api/v1/generate_music")
async def http_generate_music(request: Request):
    """流式生成音乐接口
    
    返回一个JSON行格式的流，每行包含一个事件：
    1. {"event": "start"} - 开始生成
    2. {"event": "generating", "progress": float} - 生成进度更新
    3. {"event": "completed", "audio_data": str} - 生成完成，返回base64编码的音频数据
    4. {"event": "error", "message": str} - 发生错误
    """
    try:
        # 获取请求数据
        data = await request.json()
        
        # 参数验证
        if not isinstance(data, dict) or "description" not in data:
            return JSONResponse(
                status_code=400,
                content={"error": "缺少必要的描述参数"}
            )
            
        # 返回流式响应
        return StreamingResponse(
            generate_progress_stream(data),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"Error in generate_music endpoint: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "服务器内部错误"}
        )

app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    from uvicorn.config import LOGGING_CONFIG
    
    # 配置 uvicorn 日志格式
    LOGGING_CONFIG["formatters"]["access"]["fmt"] = '%(asctime)s - %(levelname)s - %(message)s'
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = '%(asctime)s - %(levelname)s - %(message)s'
    
    # 创建配置类来设置 WebSocket 超时
    class WSConfig(uvicorn.Config):
        def __init__(self, app, **kwargs):
            super().__init__(app, **kwargs)
            # 设置 WebSocket ping 间隔和超时时间为最小值
            self.ws_ping_interval = None  # 禁用 ping
            self.ws_ping_timeout = None   # 禁用 ping 超时
            self.websocket_close_timeout = 0  # 立即关闭
    
    # 使用自定义配置运行服务器
    config = WSConfig(
        "main:app",
        host="0.0.0.0",
        port=5555,
        log_config=LOGGING_CONFIG
    )
    server = uvicorn.Server(config)
    server.run()
