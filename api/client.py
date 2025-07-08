import asyncio
import websockets
import json
import base64
import os
import uuid

class MusicGenClient:
    """音乐生成WebSocket客户端
    
    用于测试音乐生成服务的WebSocket接口
    """
    
    def __init__(self, websocket_url: str = "ws://localhost:5555"):
        """初始化客户端
        
        Args:
            websocket_url (str): WebSocket服务器地址
        """
        self.websocket_url = websocket_url
        self.client_id = str(uuid.uuid4())  # 使用UUID作为客户端ID
        
    async def connect(self):
        """连接到WebSocket服务器"""
        full_url = f"{self.websocket_url}/ws/music/{self.client_id}"
        return await websockets.connect(full_url)
    
    def save_audio(self, audio_base64: str, output_path: str = "output"):
        """保存音频文件
        
        Args:
            audio_base64 (str): Base64编码的WAV音频数据
            output_path (str): 输出目录路径
        """
        # 创建输出目录
        os.makedirs(output_path, exist_ok=True)
        
        # 解码Base64数据
        audio_data = base64.b64decode(audio_base64)
        
        # 生成输出文件路径
        output_file = os.path.join(output_path, f"music_{self.client_id}.wav")
        
        # 将音频数据写入文件
        with open(output_file, "wb") as f:
            f.write(audio_data)
            
        print(f"音频已保存到: {output_file}")
    
    async def generate_music(self, **kwargs):
        """生成音乐
        
        Args:
            description (str): 音乐描述
            **kwargs: 其他生成参数
                - duration (int): 音频时长（秒）
                - mbd (bool): 是否使用MultiBand Diffusion
                - top_k (int): top-k采样参数
                - top_p (float): top-p采样参数
                - temperature (float): 温度参数
                - cfg_coef (float): 无分类器指导系数
        """
        try:
            websocket = await self.connect()
            try:
                # 准备请求参数
                params = {
                    **kwargs
                }
                
                # 发送生成请求
                await websocket.send(json.dumps(params))
                print("已发送生成请求...")
                
                # 等待并处理响应
                while True:
                    try:
                        response = await websocket.recv()
                        data = json.loads(response)
                        
                        if data["status"] != "healthy":
                            print(f"错误: {data}")
                            break
                            
                        if data["event"] == "start":
                            print("开始生成音乐...")
                        elif data["event"] == "generating":
                            print(f"\r生成进度: {data.get('progress', 0):.2f}%", end="", flush=True)
                        elif data["event"] == "completed":
                            print("\n音乐生成完成！")
                            self.save_audio(data["audio_data"])
                            break
                    except websockets.exceptions.ConnectionClosed:
                        print("\nWebSocket连接已关闭")
                        break
                    except Exception as e:
                        print(f"\n发生错误: {str(e)}")
                        break
            finally:
                await websocket.close()
                    
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket连接已关闭")
        except Exception as e:
            print(f"发生错误: {str(e)}")

async def main():
    """测试示例"""
    # 创建客户端实例
    client = MusicGenClient(websocket_url="ws://localhost:5555")
    
    # 测试参数
    params = {
        "description": "drum and bass beat with intense percussions",
        "duration": 10,  # 生成10秒的音乐
        "mbd": False,
        "top_k": 250,
        "top_p": 0.0,
        "temperature": 1.0,
        "cfg_coef": 3.0
    }
    
    # 生成音乐
    await client.generate_music(**params)

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())
