"""Test configuration: loads the Home Assistant test harness for the whole test suite."""

import socket

import pytest
import pytest_socket  # type: ignore

pytest_plugins = ["pytest_homeassistant_custom_component"]


# The Home Assistant harness and pytest-socket block DNS and connections in every test.
# Captured here, before any test runs, so that a test can give them back.
_REAL_SOCKET = socket.socket
_REAL_CONNECT = socket.socket.connect
_REAL_GETADDRINFO = socket.getaddrinfo


@pytest.fixture
def grdf_network():
    """Lets a test reach GrDF for its own duration, and restores the guards afterwards."""

    guarded = (socket.socket, socket.getaddrinfo, _REAL_SOCKET.connect)
    pytest_socket.enable_socket()
    socket.getaddrinfo = _REAL_GETADDRINFO
    _REAL_SOCKET.connect = _REAL_CONNECT
    try:
        yield
    finally:
        socket.socket, socket.getaddrinfo, _REAL_SOCKET.connect = guarded
