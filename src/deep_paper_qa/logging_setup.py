"""loguru 日志配置：stderr + 按天轮转文件输出"""

import sys

from loguru import logger


def setup_logging() -> None:
    """配置 loguru sink：stderr 控制台 + 文件持久化。

    移除默认 handler，添加两个 sink：
    - stderr: INFO 级别，简短格式（开发时控制台查看）
    - 文件:  DEBUG 级别，按天午夜轮转，不自动清理
    """
    logger.remove()

    # stderr：简短格式
    logger.add(
        sys.stderr,
        level="INFO",
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "{message}"
        ),
    )

    # 文件：按天轮转，完整格式
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="00:00",
        retention=None,
        encoding="utf-8",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level:<8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
    )

    logger.info("日志系统初始化完成")
