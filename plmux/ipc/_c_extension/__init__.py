try:
    from plmux.ipc._c_extension._ipc_protocol import (
        FrameReader,
        encode_frame,
        decode_frame,
        MSG_INIT,
        MSG_PANE_OUTPUT,
        MSG_STATE_UPDATE,
        MSG_PANE_CLOSED,
        MSG_BELL,
        MSG_KEY,
        MSG_RESIZE,
        MSG_COMMAND,
        MSG_MOUSE,
        MSG_DETACH,
        HEADER_SIZE,
    )
except ImportError:
    from plmux.ipc.protocol import (
        FrameReader as FrameReader,
        encode_frame as encode_frame,
        decode_frame as decode_frame,
        MsgType,
    )

    MSG_INIT = MsgType.INIT
    MSG_PANE_OUTPUT = MsgType.PANE_OUTPUT
    MSG_STATE_UPDATE = MsgType.STATE_UPDATE
    MSG_PANE_CLOSED = MsgType.PANE_CLOSED
    MSG_BELL = MsgType.BELL
    MSG_KEY = MsgType.KEY
    MSG_RESIZE = MsgType.RESIZE
    MSG_COMMAND = MsgType.COMMAND
    MSG_MOUSE = MsgType.MOUSE
    MSG_DETACH = MsgType.DETACH
    HEADER_SIZE = 5
