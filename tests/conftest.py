# tests/conftest.py
"""
Pytest configuration file with shared fixtures.
"""
import pytest
import simpy
from core.simulation_model import SimulationModel
from core.entity import EventLogger


@pytest.fixture
def simple_env():
    """Create a simple SimPy environment."""
    return simpy.Environment()


@pytest.fixture
def simple_model():
    """Create a simple simulation model."""
    return SimulationModel()


@pytest.fixture
def event_logger():
    """Create an event logger."""
    return EventLogger()


@pytest.fixture
def seed_value():
    """Standard seed for reproducible tests."""
    return 12345