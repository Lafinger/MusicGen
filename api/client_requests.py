import requests
import json
import base64
import os
import uuid
import time


class MusicGenClient:
    """音乐生成客户端
    
    用于测试音乐生成服务的HTTP接口，支持SSE流式接收结果，使用同步requests库实现
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
    
    def generate_music(self, **kwargs):
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
        start_time = time.time()  # 记录开始时间
        try:
            # 准备请求参数
            params = {
                **kwargs
            }
            
            # 设置HTTP请求头
            headers = {
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            }
            
            print("正在发送生成请求...")
            # 使用stream=True参数发送请求，以支持流式获取响应
            with requests.post(
                f"{self.server_url}/api/v1/generate_music",
                json=params,
                headers=headers,
                stream=True,
                timeout=3  # 1小时超时
            ) as response:
                if response.status_code != 200:
                    print(f"错误: 服务器返回状态码 {response.status_code}")
                    print(f"错误信息: {response.text}")
                    return
                
                # 处理SSE流
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        # 空行表示数据块的结束
                        continue
                        
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])  # 去除"data: "前缀
                            
                            if "event" in data:
                                if data["event"] == "start":
                                    print("开始生成音乐...")
                                elif data["event"] == "progress":
                                    print(f"\r生成进度: {data.get('progress', 0):.2f}%", end="", flush=True)
                                elif data["event"] == "completed":
                                    end_time = time.time()  # 记录结束时间
                                    elapsed_time = end_time - start_time  # 计算经过的时间
                                    print("\n音乐生成完成！")
                                    print(f"总生成时间: {elapsed_time:.2f} 秒")
                                    if "audio" in data:
                                        self.save_audio(data["audio"])
                                    else:
                                        print("警告: 返回的数据中没有音频内容")
                                elif data["event"] == "error":
                                    end_time = time.time()  # 记录结束时间
                                    elapsed_time = end_time - start_time  # 计算经过的时间
                                    print(f"\n错误: {data.get('message', '未知错误')}")
                                    print(f"用时: {elapsed_time:.2f} 秒")
                        except json.JSONDecodeError as e:
                            print(f"解析SSE事件数据出错: {line}")
                            print(f"错误详情: {e}")
                        except Exception as e:
                            print(f"处理事件出错: {e}, 原始数据: {line}")
                                    
        except requests.exceptions.RequestException as e:
            end_time = time.time()  # 记录结束时间
            elapsed_time = end_time - start_time  # 计算经过的时间
            print(f"HTTP请求错误: {str(e)}")
            print(f"用时: {elapsed_time:.2f} 秒")
        except Exception as e:
            end_time = time.time()  # 记录结束时间
            elapsed_time = end_time - start_time  # 计算经过的时间
            print(f"发生错误: {str(e)}")
            print(f"用时: {elapsed_time:.2f} 秒")


def main():
    """测试示例"""
    # 创建客户端实例
    client = MusicGenClient(server_url="http://localhost:5555")
    
    # 测试参数
    params = {
        "description": "电子音乐带有强烈的鼓点和节奏感",
        "duration": 10,  # 生成10秒的音乐
        "mbd": False,
        "top_k": 250,
        "top_p": 0.0,
        "temperature": 1.0,
        "cfg_coef": 3.0
    }
    
    # 生成音乐
    client.generate_music(**params)


if __name__ == "__main__":
    # 运行测试
    main()
