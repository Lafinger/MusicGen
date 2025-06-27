# gunicorn配置文件
import multiprocessing

# 监听地址和端口
bind = "0.0.0.0:8888"

# 工作进程数量
workers = multiprocessing.cpu_count() * 2 + 1

# 使用uvicorn作为worker类
worker_class = "uvicorn.workers.UvicornWorker"

# 每个工作进程的超时时间（秒）
timeout = 300

# 工作进程预加载应用
preload_app = True

# 后台运行
daemon = False

# 访问日志格式
accesslog = "-"  # 标准输出
errorlog = "-"   # 标准错误输出
loglevel = "info"

# 进程名称
proc_name = "musicgen_api"

# 限制请求行的大小
limit_request_line = 0

# 限制请求字段的大小
limit_request_fields = 32768

# 限制请求字段的大小（字节）
limit_request_field_size = 0 