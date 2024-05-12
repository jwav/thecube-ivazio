import logging

def make_logger(name:str) -> logging.Logger:
    # Instantiate a logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Create a handler and set its level
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)

    # Create a formatter and add it to the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(handler)

    return logger