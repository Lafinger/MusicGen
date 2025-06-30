#!/usr/bin/env python3
import multiprocessing
import gunicorn.app.base
import logging
import torch.multiprocessing as mp

# 设置多进程启动方式为 'spawn'
mp.set_start_method('spawn')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StandaloneApplication(gunicorn.app.base.BaseApplication):
    """Gunicorn WSGI 应用程序类"""
    
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        """加载 Gunicorn 配置"""
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key.lower(), value)

    def load(self):
        """加载 WSGI 应用程序"""
        return self.application

def run_prod_server():
    """运行生产环境服务器"""
    from app import create_app  # 导入 Flask 应用
    app = create_app()

    # Gunicorn 配置
    options = {
        'bind': '0.0.0.0:5000',  # 监听地址和端口
        # 'workers': multiprocessing.cpu_count() * 2 + 1,  # 工作进程数
        'workers': 1,  # 工作进程数
        'worker_class': 'sync',  # 工作进程类型
        'timeout': 300,  # 请求超时时间（秒）
        'keepalive': 5,  # keep-alive 连接超时时间（秒）
        'accesslog': 'logs/access.log',  # 访问日志
        'errorlog': 'logs/error.log',    # 错误日志
        'loglevel': 'info',              # 日志级别
    }

    logger.info("启动生产环境服务器...")
    StandaloneApplication(app, options).run()

if __name__ == "__main__":
    run_prod_server() 