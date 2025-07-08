import os
import uuid
from contextvars import ContextVar
from pathlib import Path

from loguru import logger


# 使用任务request_id来实现全链路日志追踪
_x_request_id: ContextVar[str] = ContextVar('x_request_id', default="")  # 请求ID


class TraceID:
    """全链路追踪ID"""

    @staticmethod
    def set(req_id: str) -> ContextVar[str]:
        """设置请求ID，外部需要的时候，可以调用该方法设置
        Returns:
            ContextVar[str]: _description_
        """
        if not req_id:
            req_id = uuid.uuid4().hex
        _x_request_id.set(req_id)
        return _x_request_id


def _logger_filter(record):
    record['request_id'] = f"{_x_request_id.get()}"
    return True


def setup_logging():
    """
    配置日志系统
    """
    # 步骤1：去除默认控制台输出
    logger.remove()

    # 步骤2：定义日志格式
    log_format = (
        # 时间信息 + UUID
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | {request_id} | "
        # 日志级别，^居中对齐 8是指定宽度
        "<level>{level: ^8}</level> | "
        # 进程和线程信息
        "process [<cyan>{process}</cyan>]:<cyan>{thread}</cyan> | "
        # 文件、函数和行号
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        # 日志消息
        "<level>{message}</level>"
    )

    # 步骤3：创建日志目录
    log_dir = Path("log")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 步骤4：配置常规日志文件
    logger.add(
        str(Path(log_dir, "log.log")),
        format=log_format,
        level="INFO",
        rotation="200 MB",
        retention="1000 days",
        encoding="utf-8",
        enqueue=True,  # 异步写入
        filter=_logger_filter,
    )