from dotenv import load_dotenv, find_dotenv

dotenv_path = find_dotenv()
load_dotenv(".env", override=True)

from .log import Log
import logging
Log_ = Log(console_level = logging.INFO, # 显示控制台的等级
             log_file_name="app.log")
logger = Log_.logger
