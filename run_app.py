import logging
import os
from app import create_app
# from config import DevelopmentConfig

# 创建输出目录
os.makedirs("./logs", exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler('./logs/app.log')  # 输出到文件
    ]
)

logger = logging.getLogger(__name__)
app = create_app()
# app.config.from_object(DevelopmentConfig)

    
if __name__ == '__main__':
    logger.info("Starting Flask development server...")
    # 使用Flask的开发服务器运行应用
    app.run(host="0.0.0.0", port=5000, debug=True)
