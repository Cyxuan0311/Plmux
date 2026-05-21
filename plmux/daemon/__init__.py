"""Daemon layer: server, client, state, and transport."""

from plmux.daemon.state import ServerState, SessionHandle, serialize_state, deserialize_state
from plmux.daemon.transport import is_windows
from plmux.daemon.server import run_server
from plmux.daemon.client import is_server_alive, kill_server, connect_and_receive

_serialize_state = serialize_state
_deserialize_state = deserialize_state