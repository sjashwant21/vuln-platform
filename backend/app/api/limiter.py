from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

cfg = get_settings()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
    enabled=cfg.app_env != "test"
)
