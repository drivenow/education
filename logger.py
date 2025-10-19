import logging
import datetime
from os import makedirs
import warnings
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("markdown_it").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
warnings.filterwarnings("ignore",category=DeprecationWarning)


now_date = datetime.datetime.now().strftime('%Y-%m-%d')

# 创建一个 logger
logger = logging.getLogger("my_logger")
logger.setLevel(logging.WARNING)  # 设置日志级别为 DEBUG，记录所有级别的日志

# 创建一个处理器，输出到文本文件
makedirs("logs", exist_ok=True)
file_handler = logging.FileHandler("logs/{}.log".format(now_date))
file_handler.setLevel(logging.WARNING)  # 设置文件处理器的日志级别为 DEBUG

# 创建一个处理器，输出到控制台
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)  # 设置控制台处理器的日志级别为 DEBUG

# 创建一个格式化器，并将其添加到处理器中
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 将相同的格式化器应用到文件和控制台处理器
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 将处理器添加到 logger 中
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# # 记录一些日志
# logger.debug("这是一个调试日志")
# logger.info("这是一个信息日志")
# logger.warning("这是一个警告日志")
# logger.error("这是一个错误日志")
# logger.critical("这是一个严重错误日志")
