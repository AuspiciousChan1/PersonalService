"""Centralized application parameters with local override support."""

try:
    from .app_params_local import *  # noqa: F401,F403
except ImportError:
    from .app_params_example import *  # noqa: F401,F403

