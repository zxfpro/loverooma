import logging
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import inspect
import json
import functools
import asyncio

# 定义自定义日志级别及其对应的整数值
logging.addLevelName(25, "NOTICE")
NOTICE = 25

# 创建一个函数，用于方便地调用自定义日志级别
def notice(self, msg, *args, **kws):
    if self.isEnabledFor(NOTICE):
        self._log(NOTICE, msg, args, **kws)

logging.Logger.notice = notice

class Log:
    _instance = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, console_level = logging.INFO, log_file_name="app.log"):
        self.Console_LOG_LEVEL = console_level
        self.log_file_name = log_file_name
        self.LOG_FILE_PATH = os.path.join("logs", log_file_name)
        os.makedirs(os.path.dirname(self.LOG_FILE_PATH), exist_ok=True)
        self.logger = self.get_logger()

    def get_logger(self):
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            # --- 4. 配置 Formatter (格式化器) ---
            # 以后有一个标准化的日志要使用logger 而非标的则使用super-log
            formatter = logging.Formatter(
                "%(asctime)s $ %(created)f $ %(levelname)s $ %(funcName)s $ :%(lineno)d $ %(pathname)s $ %(message)s||"
            )
            # --- 5. 配置 Handler (处理器) ---

            # 5.1 控制台处理器 (StreamHandler)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.Console_LOG_LEVEL)  # 控制台只显示 INFO 及以上级别的日志
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

            # 文件系统
            ## 主日志本
            file_handler = RotatingFileHandler(  # RotatingFileHandler: 按文件大小轮转
                self.LOG_FILE_PATH,
                maxBytes=20 * 1024 * 1024,  # 10 MB # maxBytes: 单个日志文件的最大字节数 (例如 10MB)
                backupCount=10, # backupCount: 保留的旧日志文件数量
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)  # 记录所有日志
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            ## 运行日志本
            file_handler_info = RotatingFileHandler(
                self.LOG_FILE_PATH.replace('.log','_info.log'),
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler_info.setLevel(logging.INFO)  # 记录本系统的日志
            file_handler_info.setFormatter(formatter)
            logger.addHandler(file_handler_info)


            ## 运行日志本
            file_handler_info = RotatingFileHandler(
                self.LOG_FILE_PATH.replace('.log','_notice.log'),
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler_info.setLevel(25)  # 记录本系统的日志
            file_handler_info.setFormatter(formatter)
            logger.addHandler(file_handler_info)

            ## 错误日志本
            file_handler_warning = RotatingFileHandler(
                self.LOG_FILE_PATH.replace('.log','_error.log'),
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler_warning.setLevel(logging.WARNING)  # 记录警告和错误
            file_handler_warning.setFormatter(formatter)
            logger.addHandler(file_handler_warning)

            ## 指定日志本 
            file_handler_super = RotatingFileHandler(
                self.LOG_FILE_PATH.replace('.log','_caitical.log'),
                maxBytes=5 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler_super.setLevel(logging.CRITICAL)  # 记录重点跟踪日志
            file_handler_super.setFormatter(formatter)
            logger.addHandler(file_handler_super)

        return logger


def log_func(logger):
    def outer_packing(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            kwargs_dict = json.dumps(kwargs,ensure_ascii=False)
            try:
                if asyncio.iscoroutinefunction(func):
                    # 如果被装饰的函数是协程，则 await 它
                    result = await func(*args, **kwargs)
                else:
                    # 否则，直接调用（同步函数）
                    result = func(*args, **kwargs)
                logger.notice(f'{func.__name__} & {kwargs_dict} & {result}')
            except Exception as e:
                logger.error(f'{func.__name__} & {kwargs_dict}  & {e}')
                raise 
            return result
        return wrapper
    return outer_packing
