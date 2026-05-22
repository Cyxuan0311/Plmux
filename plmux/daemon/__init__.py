"""Daemon layer: server, client, state, and transport."""

from plmux.daemon.state import ServerState as ServerState, SessionHandle as SessionHandle, serialize_state as serialize_state, deserialize_state as deserialize_state
from plmux.daemon.transport import is_windows as is_windows
from plmux.daemon.server import run_server as run_server
from plmux.daemon.client import is_server_alive as is_server_alive, kill_server as kill_server, connect_and_receive as connect_and_receive

_serialize_state = serialize_state
_deserialize_state = deserialize_state