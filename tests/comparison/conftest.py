"""Comparison test fixtures."""

import os

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.comparison)


def pytest_configure(config):
    config.addinivalue_line("markers", "comparison: RPC comparison tests against reference node")


def pytest_runtest_setup(item):
    """Skip comparison tests if no reference URL is set."""
    if "KARSTFLOW_REFERENCE_URL" not in os.environ:
        pytest.skip("KARSTFLOW_REFERENCE_URL not set — skipping comparison test")
