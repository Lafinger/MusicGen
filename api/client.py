import asyncio
import json
import base64
import os
import uuid
import aiohttp

class MusicGenClient:
    """音乐生成客户端
    
    用于测试音乐生成服务的HTTP接口，支持SSE流式接收结果
    """
    
    def __init__(self, server_url: str = "http://localhost:5555"):
        """初始化客户端
        
        Args:
            server_url (str): 服务器地址
        """
        self.server_url = server_url
        self.client_id = str(uuid.uuid4())  # 使用UUID作为客户端ID
        
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
            # 准备请求参数
            params = {
                **kwargs
            }
            
            # 设置HTTP请求头
            headers = {
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "X-Request-Id": self.client_id
            }
            
            # 设置较大的读取缓冲区以处理大型响应块
            tcp_connector = aiohttp.TCPConnector(limit=5)
            client_timeout = aiohttp.ClientTimeout(total=3600)  # 1小时超时
            
            # 发送请求并获取SSE流
            async with aiohttp.ClientSession(connector=tcp_connector, timeout=client_timeout, 
                                            read_bufsize=1024*1024*10) as session:  # 10MB读取缓冲区
                print("正在发送生成请求...")
                async with session.post(
                    f"{self.server_url}/api/v1/generate_music", 
                    json=params,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"错误: 服务器返回状态码 {response.status}")
                        print(f"错误信息: {error_text}")
                        return
                        
                    # 处理SSE流
                    buffer = ""
                    async for line_bytes in response.content.iter_chunked(1024*1024):  # 以1MB为单位读取块
                        line = line_bytes.decode('utf-8')
                        buffer += line
                        
                        if buffer.endswith('\n\n'):
                            for event_data in buffer.split('\n\n'):
                                if event_data.startswith('data: '):
                                    try:
                                        data = json.loads(event_data[6:])  # 去除"data: "前缀
                                        
                                        if "event" in data:
                                            if data["event"] == "start":
                                                print("开始生成音乐...")
                                            elif data["event"] == "progress":
                                                print(f"\r生成进度: {data.get('progress', 0):.2f}%", end="", flush=True)
                                            elif data["event"] == "completed":
                                                print("\n音乐生成完成！")
                                                if "audio" in data:
                                                    self.save_audio(data["audio"])
                                                else:
                                                    print("警告: 返回的数据中没有音频内容")
                                                return
                                            elif data["event"] == "error":
                                                print(f"\n错误: {data.get('message', '未知错误')}")
                                                return
                                    except json.JSONDecodeError as e:
                                        print(f"解析SSE事件数据出错: {e}")
                            buffer = ""
                                    
        except aiohttp.ClientError as e:
            print(f"HTTP请求错误: {str(e)}")
        except Exception as e:
            print(f"发生错误: {str(e)}")

async def main():
    """测试示例"""
    # 创建客户端实例
    client = MusicGenClient(server_url="http://localhost:5555")
    
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
