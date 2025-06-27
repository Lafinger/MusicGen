import requests
import argparse
import os
import time
from typing import Optional
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MusicGenClient:
    """音乐生成服务的客户端类"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """初始化客户端
        
        Args:
            base_url (str): 服务的基础URL
        """
        self.base_url = base_url.rstrip('/')
        
    def check_health(self) -> bool:
        """检查服务健康状态
        
        Returns:
            bool: 服务是否健康
        """
        try:
            response = requests.get(f"{self.base_url}/api/healthcheck")
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"健康检查失败: {str(e)}")
            return False
            
    def generate_music(self, 
                      description: str, 
                      duration: int = 30,
                      mbd: bool = False,
                      top_k: int = 250,
                      top_p: float = 0.0,
                      temperature: float = 1.0,
                      cfg_coef: float = 3.0,
                      output_dir: str = "generated_music") -> Optional[str]:
        """生成音乐
        
        Args:
            description (str): 音乐描述
            duration (int): 音频时长（秒）
            mbd (bool): 是否使用MultiBand Diffusion
            top_k (int): top-k采样参数
            top_p (float): top-p采样参数
            temperature (float): 温度参数
            cfg_coef (float): 无分类器指导系数
            output_dir (str): 输出目录
            
        Returns:
            Optional[str]: 生成的音频文件路径，失败则返回None
        """
        try:
            # 准备请求参数
            params = {
                "description": description,
                "duration": duration,
                "mbd": mbd,
                "top_k": top_k,
                "top_p": top_p,
                "temperature": temperature,
                "cfg_coef": cfg_coef
            }
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 发送请求
            logger.info(f"开始生成音乐: {description}")
            start_time = time.time()
            
            response = requests.post(
                f"{self.base_url}/api/music",
                json=params,
                stream=True  # 使用流式传输处理大文件
            )
            
            if response.status_code != 200:
                error_msg = response.json().get("error", "未知错误")
                logger.error(f"生成失败: {error_msg}")
                return None
                
            # 获取当前日期时间
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 构建文件名：日期_时间_描述.wav
            filename = f"{current_time}_{description[:20]}.wav"
            filename = "".join(c for c in filename if c.isalnum() or c in ['_', '.'])  # 移除非法字符
                
            # 保存文件
            output_path = os.path.join(output_dir, filename)
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            generation_time = time.time() - start_time
            logger.info(f"音乐生成完成! 用时: {generation_time:.2f}秒")
            logger.info(f"文件保存至: {output_path}")
            
            return output_path
            
        except requests.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"生成过程出错: {str(e)}")
            return None

def main():
    """主函数，处理命令行参数并执行相应操作"""
    parser = argparse.ArgumentParser(description="音乐生成服务客户端")
    parser.add_argument("--url", type=str, default="http://localhost:5000", help="服务URL")
    parser.add_argument("--description", type=str, default="drum and bass beat with intense percussions", help="音乐描述")
    parser.add_argument("--mbd", action="store_true", help="是否使用MultiBand Diffusion")
    parser.add_argument("--duration", type=int, default=30, help="音频时长（秒）")
    parser.add_argument("--top-k", type=int, default=250, help="top-k采样参数")
    parser.add_argument("--top-p", type=float, default=0.0, help="top-p采样参数")
    parser.add_argument("--temperature", type=float, default=1.0, help="温度参数")
    parser.add_argument("--cfg-coef", type=float, default=3.0, help="无分类器指导系数")
    parser.add_argument("--output-dir", type=str, default="outputs", help="输出目录")
    
    args = parser.parse_args()
    
    # 创建客户端实例
    client = MusicGenClient(args.url)
    
    # 检查服务健康状态
    if client.check_health():
        logger.info("服务可用")
    else:
        logger.error("服务不可用")
        return
        
    # 生成音乐
    output_path = client.generate_music(
        description=args.description,
        duration=args.duration,
        mbd=args.mbd,
        top_k=args.top_k,
        top_p=args.top_p,
        temperature=args.temperature,
        cfg_coef=args.cfg_coef,
        output_dir=args.output_dir
    )
    
    if output_path:
        logger.info("音乐生成成功！")
    else:
        logger.error("音乐生成失败！")

if __name__ == "__main__":
    main()
