from controller import MusicController

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict
import asyncio
from loguru import logger
import os

# 配置日志
log_dir = "./logs"
os.makedirs(log_dir, exist_ok=True)

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

app = FastAPI(title="音乐生成服务")

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        # 存储活跃的WebSocket连接
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def send_message(self, client_id: str, json_data: Dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(json_data)
            # logger.info(f"Sent message to client {client_id}: {json_data}")


connection_manager = ConnectionManager()
music_controller = MusicController()

@app.websocket("/ws/music/{client_id}")
async def websocket_music_endpoint(websocket: WebSocket, client_id: str):
    try:
        # 接受WebSocket连接
        await websocket.accept()
        await connection_manager.connect(websocket, client_id)
        logger.info(f"WebSocket connection accepted for client {client_id}")
        
        # 创建一个异步的进度回调函数
        async def async_progress_callback(percentage: float):
            try:
                # 创建进度更新消息
                json_data = {
                    "event": "generating",
                    "progress": percentage
                }
                # 直接异步发送进度更新
                await connection_manager.send_message(client_id, json_data)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")

        # 获取当前事件循环的引用
        loop = asyncio.get_running_loop()
        
        # 创建一个同步的包装器来调用异步回调
        def sync_progress_wrapper(percentage: float):
            try:
                # 使用已保存的事件循环引用
                future = asyncio.run_coroutine_threadsafe(
                    async_progress_callback(percentage),
                    loop
                )
                # 等待回调完成，但设置超时以避免阻塞
                future.result(timeout=1)
            except Exception as e:
                logger.error(f"Error in progress wrapper: {e}")

        while True:
            try:
                # 等待接收消息
                data = await websocket.receive_json()
                logger.info(f"Received data from client {client_id}")
                
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
                
                # 正常关闭连接
                await websocket.close()
                break  # 退出循环
                
            except WebSocketDisconnect:
                logger.warning(f"WebSocket disconnected for client {client_id}")
                break
            except Exception as e:
                logger.error(f"Error processing message for client {client_id}: {e}")
                # 发送错误消息给客户端
                try:
                    await connection_manager.send_message(client_id, {
                        "event": "error",
                        "message": str(e)
                    })
                except:
                    pass
                break

    except WebSocketDisconnect:
        logger.warning(f"WebSocket disconnected during setup for client {client_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection setup for client {client_id}: {e}")
    finally:
        # 确保在任何情况下都清理连接
        connection_manager.disconnect(client_id)
        logger.info(f"Cleaned up connection for client {client_id}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5555)
