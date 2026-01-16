# agent/text/logger.py
"""
Copyright (C) 2023 Austin Berrio

A simple automated logger factory. This module provides a class `TinyLogger` to
easily create and configure logger instances for your Python applications.

The `TextLogger` class offers methods to create new loggers, set their handlers, and retrieve
existing ones. The loggers are automatically configured with a specified level (DEBUG or INFO) based
on a provided verbosity flag.

By default, the logger will output formatted log messages to the console.
"""

import sys
from logging import DEBUG, INFO, Formatter, Logger, StreamHandler, getLogger


class TextLogger:

    @classmethod
    def new_logger(cls, cls_name: str, verbose: bool) -> Logger:
        """
        Create a new logger with a specified level (DEBUG or INFO) based on the provided verbosity flag.

        :param cls_name: The name of the class that inherits from Logger.
        :param verbose: A boolean indicating whether to enable verbose logging.
        :return: Configured logger instance.
        """
        level = DEBUG if verbose else INFO
        logger = getLogger(name=cls_name)
        logger.setLevel(level)
        return logger

    @classmethod
    def set_handler(cls, logger: Logger):
        """
        Add a formatted StreamHandler to the logger if it doesn't already have any handlers.

        The logger's formatted output will be displayed on the console.
        """
        # Check if the logger has handlers to avoid adding duplicates
        if not logger.hasHandlers():
            fmt = "%(levelname)s:%(filename)s:%(lineno)d: %(message)s"
            handler = StreamHandler(stream=sys.stdout)
            formatter = Formatter(fmt=fmt)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

    @classmethod
    def get_logger(cls, cls_name: str, verbose: bool) -> Logger:
        """
        Initialize and return a Logger instance.

        :param cls_name: The name of the class that inherits from Logger.
        :param verbose: A boolean indicating whether to enable verbose logging.
        :return: Configured logger instance.
        """
        logger = TextLogger.new_logger(cls_name, verbose)
        TextLogger.set_handler(logger)
        return logger
