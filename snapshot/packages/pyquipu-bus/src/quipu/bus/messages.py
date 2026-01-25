import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def find_locales_dir() -> Path | None:
    try:
        # pyquipu-bus stores its locales in its root directory
        bus_root = Path(__file__).parent.parent
        locales_path = bus_root / "locales"
        if locales_path.is_dir():
            logger.debug(f"Found locales directory at: {locales_path}")
            return locales_path
    except (ImportError, Exception) as e:
        logger.error(f"Error finding locales directory via quipu.bus: {e}")

    logger.warning("Could not find the 'locales' directory.")
    return None
