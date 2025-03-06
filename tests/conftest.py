"""
Pytest configuration for async tests.
"""
import pytest

# Register the asyncio marker
pytest.mark.asyncio = pytest.mark.asyncio

# Configure pytest to use asyncio
pytest_plugins = ('pytest_asyncio',) 