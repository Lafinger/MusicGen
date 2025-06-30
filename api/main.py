from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json

from controller import MusicController

app = FastAPI(title="音乐生成服务")

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        # 存储活跃的WebSocket连接
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_progress(self, client_id: str, progress: float):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json({
                "event": "progress",
                "data": progress
            })

    async def send_completion(self, client_id: str, filename: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json({
                "event": "complete",
                "data": filename
            })


connection_manager = ConnectionManager()
music_controller = MusicController()


# 自定义进度回调函数
async def progress_callback(client_id: str, percentage: float):
    await connection_manager.send_progress(client_id, percentage)

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await connection_manager.connect(websocket, client_id)
    try:
        while True:
            # 等待接收消息
            data = await websocket.receive_json()
            
            if data["type"] == "generate":
                # 设置针对该客户端的进度回调
                async def client_progress_callback(generated: int, to_generate: int):
                    await progress_callback(client_id, generated, to_generate)
                
                # 设置回调函数
                music_generator.set_progress_callback(client_progress_callback)
                
                # 生成音乐
                filename = music_generator.generate_music(
                    user_prompt=data["prompt"],
                    duration=data.get("duration", 30),
                    mbd=data.get("mbd", False)
                )
                
                # 发送完成消息
                await manager.send_completion(client_id, filename)
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)

# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
