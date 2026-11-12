"""Compatibility alias for the modular vendor router."""
import sys

from . import router

sys.modules[__name__] = router
