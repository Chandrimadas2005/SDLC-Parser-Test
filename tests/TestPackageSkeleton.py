import importlib

import pytest

LAYER_PACKAGES = (
    "ParserService.Domain.Documents",
    "ParserService.Domain.Jobs",
    "ParserService.Domain.Ports",
    "ParserService.Domain.Errors",
    "ParserService.Application.UseCases",
    "ParserService.Application.Dto",
    "ParserService.Application.Errors",
    "ParserService.Infrastructure.Extraction",
    "ParserService.Infrastructure.Detection",
    "ParserService.Infrastructure.Isolation",
    "ParserService.Infrastructure.Persistence",
    "ParserService.Infrastructure.Storage",
    "ParserService.Infrastructure.Queue",
    "ParserService.Infrastructure.Http",
    "ParserService.Infrastructure.Cli",
    "ParserService.Infrastructure.Logging",
    "ParserService.Infrastructure.Config",
)


class TestPackageSkeleton:
    """The package layout from the brief (section 3.1) exists and declares __all__."""

    @pytest.mark.parametrize("module_name", LAYER_PACKAGES)
    def test_package_is_importable_and_declares_all(self, module_name: str) -> None:
        module = importlib.import_module(module_name)

        assert isinstance(module.__all__, list)
