"""Test configuration: loads the Home Assistant test harness for the whole test suite."""

import socket

import pytest
import pytest_socket  # type: ignore

pytest_plugins = ["pytest_homeassistant_custom_component"]


# The Home Assistant harness blocks DNS and sockets in every test. Captured here, before any test runs.
_REAL_GETADDRINFO = socket.getaddrinfo


@pytest.fixture
def grdf_network():
    """Lets a test reach GrDF for its own duration, and restores the harness guard afterwards."""

    guarded_getaddrinfo = socket.getaddrinfo
    socket.getaddrinfo = _REAL_GETADDRINFO
    pytest_socket.enable_socket()
    try:
        yield
    finally:
        socket.getaddrinfo = guarded_getaddrinfo
