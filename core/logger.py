import logging
import time

class Logger:
    """Класс для настройки логирования"""
    @staticmethod
    def setup_logger(log_file):
        logging.Formatter.converter = time.gmtime
        logger = logging.getLogger(log_file)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
            stream_handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s UTC [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(formatter)
            stream_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.addHandler(stream_handler)
        return logger