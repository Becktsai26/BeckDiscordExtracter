"""Shared test fixtures and Hypothesis strategies for property-based testing."""

import pytest
from hypothesis import settings

# Configure Hypothesis default settings for all property-based tests
settings.register_profile("default", max_examples=100)
settings.load_profile("default")
