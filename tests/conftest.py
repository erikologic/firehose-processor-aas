"""
Pytest configuration and shared fixtures for benchmark tests.
"""
import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Fixture providing CliRunner for all CLI tests.

    This eliminates the need to instantiate CliRunner() in every test,
    reducing duplication and improving maintainability.
    """
    return CliRunner()
