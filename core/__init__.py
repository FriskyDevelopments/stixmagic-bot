"""Shared STIX MΛGIC platform-agnostic core package."""

from .capabilities import DISCORD_CAPABILITIES, TELEGRAM_CAPABILITIES, PlatformCapabilities
from .contracts import StixCoreContract
from .engine import StixCoreEngine

__all__ = [
    "DISCORD_CAPABILITIES",
    "TELEGRAM_CAPABILITIES",
    "PlatformCapabilities",
    "StixCoreContract",
    "StixCoreEngine",
]
