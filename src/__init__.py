import logging


class ColoredFormatter(logging.Formatter):
    # 定义日志级别对应的终端颜色
    COLORS = {
        "DEBUG": "\033[34m",  # 蓝色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 洋红色
    }
    RESET = "\033[0m"  # 重置颜色

    def format(self, record):
        # 在日志级别前添加颜色
        levelname_color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{levelname_color}{record.levelname}{self.RESET}"
        return super().format(record)


# 配置日志格式
log_format = "%(levelname)s [%(filename)s:%(lineno)d] %(message)s"


handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter(log_format))

logging.basicConfig(format=log_format, level=logging.INFO, handlers=[handler])
