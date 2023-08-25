# -*- coding: utf-8 -*-
"""
Logging with configurable verbosity
Copyright (c) 2023 Prashanth Kumar
Licence: MIT
"""

import logging
import inspect
from pydantic import BaseModel
from typing import Optional


def get_frame_info(frame):
    return {
        "funcName": frame.f_code.co_name,
        "methodName": frame.f_code.co_name,
        "moduleName": frame.f_globals["__name__"],
        "className": frame.f_locals.get("self", None).__class__.__name__,
        "fileName": frame.f_globals["__file__"],
    }


class ExtraInfoFormatter(logging.Formatter):
    """
    Formatter that adds extra information to log records.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record.

        Args:
            record (logging.LogRecord): The log record.

        Returns:
            str: The formatted log message.
        """
        frame = inspect.currentframe().f_back
        while frame:
            frame = frame.f_back
            module_name = frame.f_globals["__name__"]

            if module_name != logging.__name__:
                break

        extra_info = get_frame_info(frame)

        if hasattr(record, "extra"):
            extra_info.update(record.extra)

        for key, value in extra_info.items():
            setattr(record, key, value)

        return super().format(record)


class CustomLogRecord(logging.LogRecord):
    def __init__(
        self,
        name,
        level,
        pathname,
        lineno,
        msg,
        args,
        exc_info,
        func=None,
        sinfo=None,
        **kwargs,
    ):
        super().__init__(
            name, level, pathname, lineno, msg, args, exc_info, func, sinfo
        )
        for key, value in kwargs.items():
            if not hasattr(self, key):
                setattr(self, key, value)


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


class VerbosityLogger:
    def __init__(self, logger=None, logger_name=None, verbosity=0):
        if logger is None and logger_name is None:
            # If both logger and logger_name are None, use the null logger
            self._logger = logging.getLogger("null_logger")
            self._logger.setLevel(logging.DEBUG)
            self._logger.addHandler(NullHandler())
        else:
            self._logger = logger or logging.getLogger(logger_name)

        if logger_name is not None:
            self._logger_name = logger_name
        self._verbosity = verbosity

    @property
    def logger(self):
        return self._logger
    
    @property
    def logger_name(self):
        return self._logger_name    

    @property
    def verbosity(self):
        return self._verbosity

    @verbosity.setter
    def verbosity(self, val):
        self._verbosity = val

    def log(self, level, message, verbosity=0):
        if verbosity > self._verbosity:
            return

        level_mapping = {
            "info": logging.INFO,
            "debug": logging.DEBUG,
            "error": logging.ERROR,
            "warning": logging.WARNING,
        }

        log_level = level_mapping.get(level)
        if log_level is None:
            raise ValueError("Invalid log level: {}".format(level))

        frame = inspect.currentframe().f_back
        extra_info = get_frame_info(frame.f_back)

        log_record = CustomLogRecord(
            self.logger.name,
            log_level,
            extra_info["fileName"],
            frame.f_back.f_lineno,
            message,
            (),
            None,
            func=extra_info["funcName"],
            extra=extra_info,
        )

        self._logger.handle(log_record)

    def debug(self, msg: str, verbosity: int = 0):
        self.log("debug", msg, verbosity)

    def info(self, msg: str, verbosity: int = 0):
        self.log("info", msg, verbosity)

    def warning(self, msg: str, verbosity: int = 0):
        self.log("warning", msg, verbosity)

    def error(self, msg: str, verbosity: int = 0):
        self.log("error", msg, verbosity)


class VerbosityLoggerConfig(BaseModel):
    name: Optional[str] = None
    verbosity: Optional[int] = 0

    def __init__(self, **data):
        super().__init__(**data)

        if self.name is not None:
            self._vlogger = VerbosityLogger(
                logger_name=self.name, verbosity=self.verbosity
            )
        else:
            self._vlogger = VerbosityLogger()

    @property
    def vlogger(self):
        return self._vlogger
