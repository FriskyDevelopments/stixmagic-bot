"""Shared STIX MΛGIC platform-agnostic core package."""

from core.capabilities import DISCORD_CAPABILITIES, TELEGRAM_CAPABILITIES, PlatformCapabilities
from core.engine import StixCoreEngine

__all__ = [
    "DISCORD_CAPABILITIES",
    "TELEGRAM_CAPABILITIES",
    "PlatformCapabilities",
    "StixCoreEngine",
]
