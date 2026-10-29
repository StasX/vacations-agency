"""Backward-compatible default: api.settings always selects production settings."""
from .production import *  # noqa: F401,F403
