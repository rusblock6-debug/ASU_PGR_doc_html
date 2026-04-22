from src.config import settings

from .config import get_settings as test_settings

settings.get_settings = test_settings
