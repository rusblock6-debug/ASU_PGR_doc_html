from src.core import config as app_config
from tests.config import get_settings as get_test_settings

app_config.get_settings = get_test_settings
