from controller import MusicController

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict
import asyncio
import logging
import os

# 配置日志
log_dir = "./logs"
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler('./logs/app.log')  # 输出到文件
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="音乐生成服务")

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        # 存储活跃的WebSocket连接
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def send_message(self, client_id: str, json_data: Dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(json_data)
            logger.info(f"Sent message to client {client_id}: {json_data}")


connection_manager = ConnectionManager()
music_controller = MusicController()


# 自定义进度回调函数
async def client_progress_callback(client_id: str, json_data: Dict):
    await connection_manager.send_message(client_id, json_data)

@app.websocket("/ws/music/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await connection_manager.connect(websocket, client_id)
    try:
        while True:
            # 等待接收消息
            data = await websocket.receive_json()
            
            # 创建一个同步的进度回调包装器
            def sync_progress_callback(percentage: float):
                # 创建进度更新消息
                json_data = {
                    "status": "healthy",
                    "event": "generating",
                    "progress": percentage
                }
                
                # 使用 asyncio.create_task 在事件循环中安排异步发送
                asyncio.create_task(client_progress_callback(client_id, json_data))
            
            await connection_manager.send_message(client_id, {
                "status": "healthy",
                "event": "start"
            }) 
            
            audio_data = music_controller.generate_music_with_progress(
                params=data,
                progress_callback=sync_progress_callback
            )

            await connection_manager.send_message(client_id, {
                "status": "healthy",
                "event": "completed",
                "audio_data": audio_data
            }) 

    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)

# 健康检查端点
@app.get("/api/healthcheck")
async def health_check():
    return {
        "status": "healthy"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5555, reload=True)
