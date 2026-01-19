from loguru import logger


def log_client_error(client_name: str, error: Exception) -> None:
    logger.warning("Client %s failed: %s", client_name, error)
