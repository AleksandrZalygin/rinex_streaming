import logging


def setup_logger(process_name):
    """
    This function sets up a logger with a specified process name.
    The logger is configured to output INFO level logs to the console.

    Parameters:
    process_name (str): The name of the process for which the logger is being set up.
                        This name will be used to create a unique logger name.

    Returns:
    logger (logging.Logger): The configured logger instance.
    """
    logger_name = f"RinexStreamer_{process_name}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger
