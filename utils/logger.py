import logging
import os


def setup_logger(log_file: str = "parser.log") -> logging.Logger:
    """
    Настраивает логгер для записи в файл и консоль.
    :param log_file: Имя файла для логов (по умолчанию 'parser.log').
    :return: Настроенный объект логгера.
    """
    logger = logging.getLogger("OzonParser")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
