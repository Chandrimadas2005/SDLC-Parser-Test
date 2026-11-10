"""Composition root and process entry point."""

from ParserService.Infrastructure.Bootstrap.ServiceContainer import ServiceContainer
from ParserService.Infrastructure.Bootstrap.ServiceRunner import ServiceRunner

__all__ = ["ServiceContainer", "ServiceRunner"]
