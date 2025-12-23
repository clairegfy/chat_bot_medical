"""
Pytest configuration and fixtures for validation tests.

This module provides shared fixtures for all test files in the
tests_validation directory.
"""

import pytest
from headache_assistants.nlu_hybrid import HybridNLU
from headache_assistants.nlu_v2 import NLUv2


@pytest.fixture
def hybrid_nlu():
    """
    Fixture providing a HybridNLU instance for tests.

    Returns:
        HybridNLU: Configured instance without embedding for faster tests
    """
    return HybridNLU(use_embedding=False, verbose=False)


@pytest.fixture
def nlu():
    """
    Fixture providing a HybridNLU instance for tests.

    This is an alias for hybrid_nlu to support test files that
    use 'nlu' as the fixture name.

    Returns:
        HybridNLU: Configured instance without embedding for faster tests
    """
    return HybridNLU(use_embedding=False, verbose=False)


@pytest.fixture
def nlu_v2():
    """
    Fixture providing an NLUv2 instance for tests.

    Returns:
        NLUv2: Basic rules-based NLU instance
    """
    return NLUv2()
