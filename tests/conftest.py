"""pytest configuration for Collab-Engine.

This file ensures that the project source directory is available on the
Python import path when running tests.

Location:
- tests/conftest.py
"""

import os
import sys


def pytest_configure() -> None:
    """Configure pytest to include the src directory in sys.path."""

    # Resolve repository root (one level above the tests directory)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Resolve src directory
    src_path = os.path.join(repo_root, "src")

    # Prepend src to sys.path to allow absolute imports in tests
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
