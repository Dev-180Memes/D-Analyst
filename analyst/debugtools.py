import logging
import os.path
import traceback
import sys

DEBUG = False

__all__ = ['log_debug', 'log_info', 'log_warn', 'debug_level', 'info_level', 'warning_level', 'DEBUG']

def setup_logging(level):
    """Set the logging level among debug, info, warn."""
    if level == logging.DEBUG:
        logging.basicConfig(level=level, format="%(asctime)s,%(msecs)03d  \
%(levelname)-7s  %(message)s", datefmt='%H:%M:%S')
    else:
        logging.basicConfig(level=level, format="%(levelname)-7s:  %(message)s")
    return logging.getLogger('galry')

def get_caller():
    """Return the line and module of the caller function."""
    tb = traceback.extract_stack()[-3]
    module = os.path.splitext(os.path.basename(tb[0]))[0].ljust(18)
    line = str(tb[1]).ljust(4)
    return "L:%s  %s" % (line, module)

def log_debug(obj):
    """Debug log."""
    if level == logging.DEBUG:
        string = str(obj)
        string = get_caller() + string
        logger.debug(string)
        
def log_info(obj):
    """Info log."""
    if level == logging.DEBUG:
        obj = get_caller() + str(obj)
    logger.info(obj)

def log_warn(obj):
    """Warn log."""
    if level == logging.DEBUG:
        obj = get_caller() + str(obj)
    logger.warn(obj)

def debug_level():
    logger.setLevel(logging.DEBUG)

def info_level():
    logger.setLevel(logging.INFO)

def warning_level():
    logger.setLevel(logging.WARNING)

if DEBUG:
    level = logging.DEBUG
else:
    level = logging.WARNING
logger = setup_logging(level)
logger.setLevel(level)

if __name__ == '__main__':
    log_debug("hello world")
    log_info("hello world")