"""Auto-apply errors marker to all tests in errors/ directory."""

from __future__ import annotations

import pytest

# Apply the 'errors' marker to all tests in this directory
pytestmark = pytest.mark.errors


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Add errors marker to all items in this directory."""
    for item in items:
        if "/errors/" in str(item.fspath):
            item.add_marker(pytest.mark.errors)
