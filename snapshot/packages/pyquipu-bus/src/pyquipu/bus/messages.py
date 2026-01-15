import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def find_locales_dir() -> Path | None:
    """
    Locates the 'locales' directory which is stored in the pyquipu-common package.
    """
    try:
        import pyquipu.common
        # pyquipu-common stores its locales in its root directory
        common_root = Path(pyquipu.common.__file__).parent
        locales_path = common_root / "locales"
        if locales_path.is_dir():
            logger.debug(f"Found locales directory at: {locales_path}")
            return locales_path
    except (ImportError, Exception) as e:
        logger.error(f"Error finding locales directory via pyquipu.common: {e}")

    logger.warning("Could not find the 'locales' directory.")
    return None